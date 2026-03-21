FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/worker/pyproject.toml /app/pyproject.toml
COPY services/worker/README.md /app/README.md
COPY services/worker/worker /app/worker

RUN pip install --no-cache-dir .

CMD ["arq", "worker.queue.WorkerSettings"]
