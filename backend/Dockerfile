# syntax=docker/dockerfile:1
FROM python:3.12-slim

# INSTALL_DEV=true adds test and tooling dependencies (used by compose for development).
ARG INSTALL_DEV=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/

# Runtime libraries for ONNX Runtime (OCR) and OpenCV.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first so code edits don't invalidate the layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-install-project --no-dev; \
    fi

COPY . .

RUN useradd --create-home --uid 10001 nabz \
    && mkdir -p /data/uploads /srv/data \
    && chown -R nabz /app /data /srv/data
USER nabz

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
