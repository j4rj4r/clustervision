FROM python:3.12-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
# Without this, Python's stdout is block-buffered (not line-buffered) since
# it isn't a TTY — app-level log.error() calls (e.g. the Kubernetes API
# error logged before being sanitized into the generic 403 response) can
# sit unflushed in a worker's buffer indefinitely under low request volume,
# never reaching `kubectl logs` until enough other output forces a flush.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -r -u 1000 -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

USER appuser

EXPOSE 8000

# WEB_CONCURRENCY controls the number of Gunicorn worker processes.
# Default to 2 for in-cluster deployments; override via env if needed.
ENV WEB_CONCURRENCY=2

ENTRYPOINT ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers $WEB_CONCURRENCY --bind 0.0.0.0:8000 --access-logfile - --error-logfile - --no-control-socket"]
