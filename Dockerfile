# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools for bcrypt native extension
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: production image ─────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=appuser:appuser . .

# Drop privileges
USER appuser

# Gunicorn — match Render's Procfile config
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn app:app --workers 2 --timeout 60 --bind 0.0.0.0:${PORT}"]
