from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
