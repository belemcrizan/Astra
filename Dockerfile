# Multi-stage Dockerfile for ASTRA v0.3 (Local and Google Cloud Run)
FROM python:3.13-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    ASTRA_OUTPUT_DIR=/app/artifacts

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code
COPY pyproject.toml ./
COPY src/ ./src/
COPY fixtures/ ./fixtures/

# Install dependencies including FastAPI and Uvicorn
RUN pip install --no-cache-dir -e ".[api]"

# Expose port for Cloud Run
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start FastAPI server
CMD ["sh", "-c", "uvicorn astra_poc.api:app --host 0.0.0.0 --port ${PORT}"]
