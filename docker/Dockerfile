# Dockerfile

# ── Base Image ─────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# ── System Dependencies ────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python Dependencies ────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy Application Code ──────────────────────────
COPY . .

# ── Create necessary directories ───────────────────
RUN mkdir -p \
    data/raw \
    data/clean \
    chroma_db \
    logs

# ── Expose Port ────────────────────────────────────
EXPOSE 8000

# ── Health Check ───────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start Command ──────────────────────────────────
CMD ["uvicorn", "api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]