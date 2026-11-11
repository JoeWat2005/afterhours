> [!WARNING]
> **Deprecated: no longer maintained.** Built as a university team project and last updated in March 2026; kept for reference.

# After Hours

A mobile app for getting around cities safely at night: an Expo / React Native client backed by a FastAPI service that plans walking and public transport routes and scores them for safety, speed and accessibility.

**Status:** deprecated prototype, built as a university team project. It is not production-ready; see [Notes](#notes).

After Hours is aimed at students, residents and tourists who need more information late at night than a standard route app provides. The project aligns with UN Sustainable Development Goal 11, which focuses on safer and more accessible cities.

## Features

- Night-time route planning: walking routes from Mapbox Directions and walking-plus-transit options from Google Directions, ranked by the user's choice of maximum safety, balanced or most efficient
- A safety estimate for each route: an empirical Bayes model that combines police crime data from data.police.uk with user reports, adjusted for time of day and street lighting
- Route details from OpenStreetMap (Overpass API): street lighting, steps, lifts, ramps, escalators, wheelchair access, venues and transit stops near the route
- Must-have filters for accessibility (avoid stairs, step-free access, lifts, ramps, escalators) and for waiting areas (safe or well-lit waiting areas, Wi-Fi, staffed or open venues nearby)
- Safety reports: users can flag crime, harassment, poor lighting or unsafe areas; reports are checked by the API and shared in real time through Convex
- Map layers for an incident heatmap, report pins, transit and nearby emergency services (hospitals, police, fire and ambulance stations)
- Sign-in with Clerk; the API verifies Clerk tokens against the issuer's public keys
- High-contrast mode

A demo walkthrough video (`apps/mobile/demo.mov`) and an Android build (`apps/mobile/afterhours.apk`) are stored with Git LFS.

## Tech stack

| Area | Technologies |
|---|---|
| Mobile app | Expo SDK 55, React Native 0.83, React 19, TypeScript, Expo Router, NativeWind, Clerk, Convex, Mapbox (`@rnmapbox/maps`) |
| API | Python 3.13, FastAPI, Uvicorn, SQLAlchemy (async), psycopg 3, GeoAlchemy2, Alembic, httpx |
| Worker | ARQ on Redis |
| Data | PostgreSQL with PostGIS, Redis, Convex |
| External data | data.police.uk, OpenStreetMap Overpass API, Mapbox Directions and Geocoding, Google Directions and Places |
| Infrastructure | Docker, Docker Compose, Terraform for AWS (ECS Fargate, RDS PostgreSQL, ElastiCache Redis) |
| Testing and tooling | pytest, pytest-asyncio, Ruff, mypy |

## Getting started

### Prerequisites

- Node.js 22 (`.nvmrc`) and npm 11
- Python 3.13 (`.python-version`)
- Docker Desktop, for the local database and Redis
- Accounts or keys for Clerk, Convex, Mapbox and Google Maps
- Terraform 1.11 or later, only if you are working on the AWS infrastructure

### Cloning

The repository stores a 188 MB APK and a 98 MB video with Git LFS. To skip downloading them, set `GIT_LFS_SKIP_SMUDGE=1` when cloning. On Windows, the committed Android build output has very long file paths, so clone with long paths enabled:

```bash
git -c core.longpaths=true clone https://github.com/JoeWat2005/afterhours.git
cd afterhours
```

### Configuration

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

The API and the worker read `.env` from the repository root and from their own service folders.

| Variable | Used by | Purpose |
|---|---|---|
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | App | Clerk publishable key |
| `EXPO_PUBLIC_CONVEX_URL` | App | Convex deployment URL |
| `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` | App, API | Mapbox token for the map and geocoding, and for Mapbox walking directions in the API |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | App, API | Google key for nearby emergency services in the app; the API falls back to it for transit directions |
| `EXPO_PUBLIC_API_BASE_URL` | App | Base URL of the FastAPI service |
| `CLERK_ISSUER_URL`, `CLERK_JWT_ISSUER_DOMAIN` | API, Convex | Clerk issuer used to verify sign-in tokens. The API accepts either name; Convex reads `CLERK_JWT_ISSUER_DOMAIN` from its own deployment settings |
| `CONVEX_DEPLOYMENT_URL` | API | Convex deployment URL |
| `APP_ENV` | API, worker | Environment name; `development` turns on SQL logging |
| `API_PREFIX` | API | Path prefix for all routes, `/v1` in the example |
| `HOST`, `PORT`, `RELOAD` | API | Server address, port and auto-reload, used by the `afterhours-api` command |
| `DATABASE_URL` | API | PostgreSQL/PostGIS connection string |
| `REDIS_URL` | API | Redis connection string |
| `WORKER_REDIS_URL`, `WORKER_API_BASE_URL`, `WORKER_NOTIFICATION_BATCH_SIZE` | Worker | Worker queue, API address and notification batch size |
| `ROUTE_SCORE_WEIGHT_SAFETY`, `ROUTE_SCORE_WEIGHT_SPEED`, `ROUTE_SCORE_WEIGHT_ACCESSIBILITY` | API | Weights for the basic route score |
| `GOOGLE_MAPS_API_KEY` | API | Google key for transit directions |

`.env.example` also lists `LOG_LEVEL` and `CLERK_SECRET_KEY`, which the current code does not read.

### Running the mobile app

```bash
npm install
npx convex login
npx convex dev
npm run mobile:start
```

The app depends on native modules such as `@rnmapbox/maps` and uses `expo-dev-client`, so build and run it with `npm run mobile:android` or `npm run mobile:ios`. `npm run mobile:typecheck` runs the TypeScript checks.

### Running the backend locally

Start PostGIS and Redis:

```bash
docker compose -f infra/local/docker-compose.yml up -d
```

Set up and start the API (OpenAPI docs are served at `/docs`):

```bash
cd services/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

On Windows, `python run_api.py` starts the API on `127.0.0.1:8000` using the selector event loop. After the migrations, `python seed.py` adds sample safety reports for a demo.

Set up and start the worker:

```bash
cd services/worker
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
arq worker.queue.WorkerSettings
```

`services/api/docker-compose.yml` is an alternative that runs PostGIS, Redis and the API together. It applies migrations and seeds data first, and reads `services/api/.env`. Start it with `docker compose up --build` from `services/api`.

### Tests

The root `pyproject.toml` points pytest at both services, so run it from the repository root with the API and worker packages installed:

```bash
pytest
```

Some tests are skipped unless you opt in:

| Variable | Enables |
|---|---|
| `TEST_POSTGRES_DATABASE_URL` | Postgres integration tests against a real database |
| `TEST_MIGRATION_DATABASE_URL` | Alembic migration round-trip tests |
| `RUN_LIVE_ROUTE_TEST=1`, `ROUTE_TEST_BASE_URL` | End-to-end route test against a running API |

`testing.md` and `FINAL_TESTING_REPORT.md` describe the test strategy and recorded results.

### Deployment

- **Containers:** `docker/api.Dockerfile` and `docker/worker.Dockerfile` build the API and worker images, using the repository root as the build context.
- **AWS:** `infra/terraform/envs/dev` composes modules for the network, an ECS Fargate cluster, RDS PostgreSQL, ElastiCache Redis and the API and worker services (default region `eu-west-2`). It is a scaffold: secrets handling, CI/CD, load balancer rules and NAT gateways are intentionally missing. See `infra/terraform/README.md`.
- **Mobile builds:** EAS profiles are defined in `apps/mobile/eas.json`; `preview` produces an internally distributed Android APK, and `development` builds a development client.
- **Convex:** `npm run convex:deploy` deploys the Convex functions.

## How it works

```text
Mobile app (Expo) ──── Clerk sign-in
   │   │
   │   └── Convex: real-time journeys, safety reports and users
   │
   └── FastAPI (/v1) ── PostgreSQL + PostGIS
          │
          ├── Mapbox and Google Directions (candidate routes)
          ├── Overpass / OpenStreetMap (lighting, accessibility, venues)
          └── data.police.uk (crime data)

Worker (ARQ + Redis) ── scheduled background jobs
```

- **Mobile app** (`apps/mobile`): Expo Router screens live in `app/`; `app/(tabs)/index.tsx` is the main map with route planning, reports, the heatmap and nearby services. `src/lib/api.ts` calls the API with the user's Clerk token and handles Mapbox geocoding and Google place search. `src/providers/AppProviders.tsx` sets up Clerk and Convex.
- **Convex** (`convex/`): the schema (`schema.ts`) has `journeys`, `safetyReports` and `users` tables, with queries and mutations in `journeys.ts`, `reports.ts` and `users.ts`. Authentication is configured for Clerk in `auth.config.ts`.
- **API** (`services/api`): `app/main.py` creates the FastAPI app and mounts the routers under `API_PREFIX`. `app/api/deps/auth.py` verifies Clerk tokens. `app/integrations/` wraps the external services, and `app/services/` holds the route logic: geometry, enrichment, the safety estimator (tuned in `app/core/route_risk_config.py`), scoring, requirement checks, ranking, overlays, the heatmap and nearby emergency services. Models are in `app/models/`, and Alembic migrations in `alembic/versions/`.
- **Worker** (`services/worker`): `worker/queue.py` registers ARQ cron jobs to ingest transport feeds (hourly), aggregate heatmaps and schedule notifications (both every 15 minutes).

## Project structure

```text
.
├── android/              Generated Android project and build output from a root-level Expo prebuild
├── apps/
│   └── mobile/           Expo / React Native app (also contains a generated ios/ project)
├── convex/               Convex schema and functions
├── docker/               Dockerfiles for the API and worker
├── docs/                 Architecture plan, team conventions and backend notes
├── infra/
│   ├── local/            Docker Compose for local PostGIS and Redis
│   └── terraform/        AWS infrastructure scaffold
├── packages/
│   └── contracts/        Shared TypeScript contracts
├── services/
│   ├── api/              FastAPI backend, Alembic migrations and tests
│   └── worker/           ARQ background worker and tests
├── test_evidence/        Screenshots of test runs
├── package.json          npm workspaces and app scripts
└── pyproject.toml        pytest, Ruff and mypy configuration
```

More documentation:

- [Architecture plan](docs/architecture.md)
- [Team conventions](docs/conventions.md): branches, pull requests and commit messages
- [Backend notes](docs/backend/README.md)
- [Terraform notes](infra/terraform/README.md)

## Notes

- In this snapshot, `services/api/app/api/router.py` mounts only the health endpoints and a basic route-scoring router. The journeys, reports, heatmap, services and users route modules, and the `/routes/plan` and `/routes/overlays` endpoints that the mobile app calls, are not wired in, although the integration tests expect them.
- `apps/mobile/app/index.tsx` imports `src/features/map/useEmergencyServices`, but the committed file is `useEmergencyService` with no file extension, so the app is unlikely to bundle until that is fixed. Google place search in `src/lib/api.ts` reads `env.googleMapsApiKey`, which `src/lib/env.ts` does not define.
- The worker jobs in `services/worker/worker/jobs.py` are placeholders that return a `stubbed` status.
- The API reads `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` and `GOOGLE_MAPS_API_KEY` with `os.getenv`. When you run it directly, export them in its environment, because the settings loader reads `.env` without setting environment variables.
- The set-up steps create `.env` at the repository root. Expo normally reads `EXPO_PUBLIC_*` variables from the app's own folder, so you may also need a copy in `apps/mobile/`.
- `services/api/.env.example` omits settings the API requires, such as `API_PREFIX`, `HOST`, `PORT`, `RELOAD` and the `ROUTE_SCORE_WEIGHT_*` values; copy them from the root `.env.example`.
- `app/core/config.py` and `worker/config.py` locate the repository root with `Path(__file__).resolve().parents[...]`. That parent does not exist at the paths used inside the Docker images, so the containers are likely to fail at start-up until this is changed.
- The Terraform Postgres module uses a placeholder database password; replace it with a managed secret before applying.
