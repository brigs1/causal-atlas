# Cross-Species Causal Atlas — Cloud Run 컨테이너
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY web/ /app/web/
COPY index.html kg.min.json.gz /app/
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1
# Cloud Run은 $PORT 주입(기본 8080)
CMD ["sh","-c","exec uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
