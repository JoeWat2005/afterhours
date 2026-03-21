# API Service

FastAPI runtime for the scored-routing backend. This service owns:

- request validation and OpenAPI generation
- journey/report persistence against PostgreSQL/PostGIS
- route scoring orchestration and safety report checks
- health and readiness endpoints for ECS/Fargate

## Local dev

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

The service expects a PostgreSQL/PostGIS database and Redis instance. Use
`infra/local/docker-compose.yml` to get those running quickly.
