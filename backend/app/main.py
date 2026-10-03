from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.routes import (
    admin,
    ask,
    auth,
    care,
    catalogue,
    catalogue_admin,
    clinicians,
    explanations,
    insights,
    profiles,
    records,
    reports,
    review,
    shares,
)
from app.core.config import settings
from app.db import engine

_weak_key = len(settings.secret_key) < 32 or settings.secret_key.startswith("development-only")
if settings.app_env != "development" and _weak_key:
    raise RuntimeError("Set SECRET_KEY (32+ characters) outside development")

app = FastAPI(title="Nabz API", version="0.3.0")

# Every API response (docs/10 §4, ASVS 5.0 V3): no sniffing, framing or referrer; JSON says it is UTF-8; JSON bodies
# may load nothing; and HSTS once the API is served over HTTPS. Files keep their own Content-Disposition.
SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cross-origin-resource-policy": "same-origin",
}
JSON_TYPES = ("application/json", "application/problem+json")


class SecurityHeaders:
    def __init__(self, inner: ASGIApp):
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                kind = headers.get("content-type", "")
                if kind.startswith(JSON_TYPES):
                    headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
                    if "charset" not in kind:
                        headers["content-type"] = f"{kind}; charset=utf-8"
                if settings.cookie_secure:
                    headers.setdefault("strict-transport-security", "max-age=31536000; includeSubDomains")
            await send(message)

        await self.inner(scope, receive, with_headers)


app.add_middleware(SecurityHeaders)
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(reports.router)
app.include_router(catalogue.router)
app.include_router(insights.router)
app.include_router(explanations.router)
app.include_router(records.router)
app.include_router(shares.router)
app.include_router(care.router)
app.include_router(ask.router)
app.include_router(review.router)
app.include_router(admin.router)
app.include_router(clinicians.router)
app.include_router(catalogue_admin.router)

PROBLEM = "application/problem+json"


@app.exception_handler(HTTPException)
async def problem(request: Request, exc: HTTPException) -> JSONResponse:
    """RFC 9457 problem details. Extra fields (e.g. `report_id`) come from a dict `detail`."""
    extra = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    body = {"type": "about:blank", "title": _TITLES.get(exc.status_code, "Error"), "status": exc.status_code, **extra}
    return JSONResponse(body, status_code=exc.status_code, media_type=PROBLEM, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    body = {"type": "about:blank", "title": "Invalid request", "status": 422,
            "detail": "Some fields need attention.", "errors": errors}
    return JSONResponse(body, status_code=422, media_type=PROBLEM)


_TITLES = {400: "Bad request", 401: "Not signed in", 403: "Not allowed", 404: "Not found", 409: "Conflict",
           422: "Invalid request"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> JSONResponse:
    """Readiness: the database is reachable and pgvector is installed."""
    try:
        with engine.connect() as conn:
            pgvector = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable", "database": "unreachable"}, status_code=503)
    return JSONResponse({"status": "ready", "database": "ok", "pgvector": pgvector})
