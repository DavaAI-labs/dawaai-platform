# Dockerfile — DavaAI v5 backend
#
# Multi-stage build:
#   Stage 1 (builder) — install Python deps into a venv
#   Stage 2 (runtime) — copy only the venv + app code; no build tools in prod
#
# Why non-root: running as root in a container violates least-privilege and
# fails security scans (Snyk, Trivy) that many CI pipelines enforce.

# ── Stage 1: dependency builder ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps (needed for some C-extension packages like rapidfuzz)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtualenv so the runtime stage can copy it cleanly
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false dawaai

WORKDIR /app

# Copy only the venv (no gcc, no pip, no build artifacts)
COPY --from=builder /build/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy application code
COPY backend/ .

# Data directory (medicines CSV, corrections JSONL, bills JSON)
# Mounted as a volume in production so data survives container restarts.
RUN mkdir -p /app/data/medicine_db /app/data/corrections \
    && chown -R dawaai:dawaai /app

USER dawaai

# Uvicorn with multiple workers for production.
# --workers 4 is a sensible default for a 2-vCPU host.
# Override with the WORKERS env var at deploy time.
ENV WORKERS=4
ENV PORT=8000

EXPOSE 8000

# Healthcheck so Railway/Render/ECS know when the container is ready
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS}"]
