# After Hours

After Hours is a mobile app aimed at people moving around cities at night, especially students, residents and tourists who want more useful information than a standard route app can usually provide during later hours.

The app is meant to help people:

- find safer routes after dark
- check late-night public transport and arrivals
- find nearby Wi-Fi, emergency services and useful open places
- filter routes by specific needs
- report areas that feel less safe due to lighting, crime, or general sketchiness

The project also aligns with UN Sustainable Development Goal 11 by focusing on safer and more accessible urban travel at night.

## Repo Structure

```text
.
├── apps/
│   └── mobile/              Expo / React Native app (includes convex/ and android/)
├── docs/                    Main project docs
├── docker/                  Dockerfiles for API and worker
├── infra/
│   ├── local/               Local Postgres + Redis
│   └── terraform/           AWS deployment scaffold
├── packages/
│   └── contracts/           Shared TypeScript contracts
├── services/
│   ├── api/                 FastAPI backend
│   └── worker/              Background jobs
├── .env.example             Example env vars
├── package.json             Root JS workspace config
└── pyproject.toml           Root Python tool config
```

## Docs

Start here, then follow what you need:

- [Team conventions](./docs/conventions.md)
- [Architecture plan](./docs/architecture.md)
- [Backend notes](./docs/backend/README.md)
- [Terraform notes](./infra/terraform/README.md)

Please read the conventions doc first so the branch and PR workflow stays clean and consistent.

## Tech Stack

There is an [example .env file](./.env.example) at the repo root with example environment variables, please run `cp .env.example .env` to create your own version and add it to [gitignore](./.gitignore) so you don't expose keys and passwords.

### Frontend

- Expo SDK 55
- React Native 0.83
- TypeScript
- Expo Router
- NativeWind
- Clerk
- Convex
- Mapbox

### Backend

- Python 3.13
- FastAPI
- Uvicorn
- SQLAlchemy
- Psycopg
- Redis
- ARQ
- PostGIS / GeoAlchemy2
- Alembic

### Infra

- Docker
- Terraform
- AWS ECS / Fargate
- AWS RDS PostgreSQL + PostGIS
- AWS ElastiCache Redis

## Quick Setup

### What you need

- Node 22
- npm 11
- Python 3.13
- Docker Desktop

Terraform is only needed if you are doing backend AWS infra stuff.

### Frontend setup

```bash
npm install
cp .env.example .env
cd apps/mobile && npx convex login   # once per machine
npm run convex:dev                   # from repo root; or: cd apps/mobile && npx convex dev
npm run mobile:start
```

Convex’s project root is `apps/mobile` (where `convex/` lives).

If you are working on the map features, you will need a valid Mapbox token in `.env`.

### Local backend setup

Start local services:

```bash
docker compose -f infra/local/docker-compose.yml up -d
```

Set up the API:

```bash
cd /Users/benjamincheesebrough/Desktop/AlgorithmAvengers/services/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main
```

Set up the worker:

```bash
cd /Users/benjamincheesebrough/Desktop/AlgorithmAvengers/services/worker
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m worker.main
```

## How We Use The Repo

- `main` = stable branch
- `develop` = shared integration branch
- feature work goes on feature branches and gets PR'd into `develop`

Read the full workflow in [docs/conventions.md](./docs/conventions.md).

## Short Project Plan

The rough build order is:

1. get the core frontend/backend skeleton in place
2. wire auth and basic account flow
3. build the map-based route experience
4. add crime / lighting / transport overlays and filters
5. add user reporting
6. tighten up caching, offline behaviour, and edge cases
