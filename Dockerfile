FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Default command is overridden per-service in docker-compose.yml.
CMD ["spacer"]
