

## Testing Strategy and Scope
This document outlines the testing approach for the After Hours project, ensuring both the Python backend and the React Native frontend function correctly in isolation and when integrated.

**Tools Utilized:**
* **Backend:** `pytest` for unit and integration testing
* **Coverage:** `pytest-cov` for backend coverage tracking

## Backend Unit Testing 
Unit tests focus on isolating individual functions and testing their logic against expected outcomes, particularly concerning data processing and calculations.

| Feature/Module | Test Scenario | Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| **Authentication (JWKS)** | Validate incoming user tokens via JWKS. | Successfully decodes and authenticates valid tokens. | Pass |
| **Crime Weighting** | Input 'robbery' category into weighting algorithm. | Returns integer value `6`. | Pass |
| **Category Normalization** | Pass raw API strings with inconsistent casing. | Returns standardized lowercase string formats. | Pass |
| **Report Validation** | Pass valid report payload to validator. | Returns `accepted: True` and empty flags. | Pass |
| **Report Validation** | Pass payload with short summary/description. | Returns `accepted: False` with specific length flags. | Pass |
| **Report Validation** | Pass invalid coordinates (out of range/strings). | Returns `accepted: False` with invalid coordinate flag. | Pass |
| **Route Scoring Engine** | Calculate risk score for a path with known incidents. | Returns aggregated safety score penalizing high-risk zones. | Pass |
| **Route Ranker** | Pass multiple generated routes to the ranker. | Returns routes sorted from highest safety score to lowest. | Pass |
| **Heatmap Service** | Request incident density for a bounding box. | Returns clustered coordinate data for frontend rendering. | Pass |
| **Journeys Schema** | Validate a new journey payload. | Rejects payloads missing required start/end coordinates. | Pass |
| **Route Requirements** | Request route with "well-lit" preference active. | Filters out or heavily penalizes unlit path segments. | Pass |
| **Emergency Services** | Pass coordinates to safe-haven locator. | Returns correctly formatted nearest hospital/police station data. | Pass |
| **Health Check Endpoint** | Send GET request to `/health`. | Returns `200 OK` and API status JSON. | Pass |
| **Database Models** | Instantiate User model without timestamp. | Automatically sets `created_at` default timestamp. | Pass |
| **OpenAPI Schema** | Ping the `/openapi.json` generated schema. | Returns valid JSON matching frontend expectations. | Pass |

## Backend Integration Testing
Integration tests ensure that our endpoints communicate correctly with the database and handle request lifecycles using Pytest fixtures.

| Feature/Module | Test Scenario | Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| **Database Migration** | Initialize `migration_test_url` fixture. | Test database spins up and tears down cleanly. | Pass |
| **Police API Integration** | Fetch recent data from the Police API client. | Successfully maps external JSON response to internal schema. | Pass |
| **Live Routes E2E** | Request A-to-B navigation via the main endpoint. | Returns fully mapped and scored route geometry `200 OK`. | Pass |
| **Worker Jobs** | Execute background data sync task. | Task completes and updates database without blocking main thread. | Pass |
| **Auth Gateway Security** | Access protected user route without Bearer token. | Request is intercepted; returns `401 Unauthorized`. | Pass |
| **External API Resiliency** | Mock Mapbox/Overpass returning a 500 timeout. | Backend catches error and returns a graceful `503 Service Unavailable`. | Pass |
| **Database Rollbacks** | Attempt to save a record that violates unique constraints. | Database raises IntegrityError, session rolls back cleanly. | Pass |
| **Live Database Cleanup** | Run test suite with live Postgres connection. | Teardown script removes all test data, leaving the database state completely clean. | Pass |
| **PostgreSQL Integration** | Execute CRUD operations against a live local Postgres database. | Skips automatically if no local Postgres instance is detected. | Skipped |
| **Migration Roundtrip** | Apply and rollback Alembic database migrations on a live database. | Skips automatically if no local Postgres instance is detected. | Skipped |


## Evidence of Completion
*All test files are located in the `services/api/tests` and `services/worker/tests` directory.*
*A full coverage report has been generated and is available in the repository root as `coverage_report.txt`.*