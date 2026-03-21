# Backend Notes

## Runtime split

- `services/api`: HTTP-facing FastAPI service
- `services/worker`: Redis-backed async worker
- `infra/local`: Docker Compose for local PostGIS + Redis
- `infra/terraform`: AWS deployment layout

## Why this split

The diagram already separates request/response traffic from long-running jobs.
Keeping API and worker in separate services means:

- API latency stays predictable
- background jobs can scale independently
- ingestion/aggregation failures do not take the API down
