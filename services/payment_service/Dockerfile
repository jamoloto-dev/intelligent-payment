FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY shared/ /app/shared/
COPY services/payment_service/ /app/services/payment_service/

RUN pip install --no-cache-dir .

EXPOSE 8005

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "services.payment_service.app.main:app", "--host", "0.0.0.0", "--port", "8005"]
