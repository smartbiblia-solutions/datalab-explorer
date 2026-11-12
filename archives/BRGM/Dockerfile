# Dockerfile
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl vim build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage caching for deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest afterwards
COPY . .

VOLUME ["/app/instance", "/app/static/data/uploads"]
EXPOSE 5000
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--timeout=0", "--workers=2", "app:create_app()"]