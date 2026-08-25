FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Default: serve the web app (and any bots whose tokens are set).
# The docker-compose.yml overrides this per-service (web / slack / discord).
CMD ["python", "app.py"]
