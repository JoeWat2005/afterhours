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

## Running the app

You need **Docker Desktop** and **Node 22+** installed. That is basically it.

### 1. Start the backend

```bash
cd services/api
cp .env.example .env
docker compose up --build
```

This starts Postgres (with PostGIS), Redis and the API on `localhost:8000`. It runs migrations and seeds the database with sample reports automatically, so there is something to look at on first load.

### 2. Start the mobile app

```bash
npm install
cd apps/mobile
npx expo start
```

Press `i` for the iOS simulator or `a` for Android. The app points at `localhost:8000` by default.

On the sign in screen you can tap **Try demo** to skip authentication and go straight to the map. This works without a Clerk account, the backend accepts unauthenticated requests in development mode.

If you want to sign in properly, use a Clerk account registered under the project’s publishable key.

### 3. iOS simulator location

The iOS simulator defaults to San Francisco. To set it to Birmingham (where the heatmap and seed data are):

```bash
xcrun simctl location booted set 52.4862,-1.8904
```

### Running on Android

There is no `android/` folder committed because EAS cloud builds regenerate it. If you want to build locally you would need Android Studio, then:

```bash
cd apps/mobile
npx expo prebuild --platform android
npx expo run:android
```

Alternatively we have an EAS build profile that produces an APK in the cloud without needing Android Studio:

```bash
cd apps/mobile
npx eas build --profile preview --platform android
```

### Running the tests

```bash
cd services/api
source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/unit/ -v          # fast, no external deps
pytest tests/integration/ -v   # needs postgres running
```

### Known issues

- In demo mode (unauthenticated), user report pins don’t appear on the map. The heatmap, route planning, services and report submission all work fine. We think it is a timing issue with how the sync fires before the demo flag propagates, but ran out of time to fix it.
- The Android APK build via EAS is set up but hasn’t been fully tested end to end on a device yet.

### Environment variables

The `.env.example` in `services/api/` has everything documented. The root `.env` has the mobile app keys (Mapbox, Clerk, Google Maps). API keys are included for development use only.

## How we used the repo

- `main` = stable branch
- `develop` = shared integration branch
- feature work went on feature branches and got PR’d into `develop`

Read the full workflow in [docs/conventions.md](./docs/conventions.md).
