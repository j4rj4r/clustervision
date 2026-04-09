FROM python:3.12-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app

RUN useradd -r -u 1000 -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

USER appuser

EXPOSE 8000

# WEB_CONCURRENCY controls the number of Gunicorn worker processes.
# Default to 2 for in-cluster deployments; override via env if needed.
ENV WEB_CONCURRENCY=2

CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers $WEB_CONCURRENCY --bind 0.0.0.0:8000 --access-logfile - --error-logfile -"]
