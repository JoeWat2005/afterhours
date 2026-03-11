FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/api/pyproject.toml /app/pyproject.toml
COPY services/api/README.md /app/README.md
COPY services/api/app /app/app
COPY services/api/alembic /app/alembic
COPY services/api/alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
