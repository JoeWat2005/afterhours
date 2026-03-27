

## Testing Strategy and Scope
This document outlines the testing approach for the After Hours project, ensuring both the Python backend and the React Native frontend function correctly in isolation and when integrated.

**Tools Utilized:**
* **Backend:** `pytest` for unit and integration testing
* **Coverage:** `pytest-cov` for backend coverage tracking

## Backend Unit Testing (Python)
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

## Backend Integration Testing
Integration tests ensure that our endpoints communicate correctly with the database and handle request lifecycles using Pytest fixtures.

| Feature/Module | Test Scenario | Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| **Database Migration** | Initialize `migration_test_url` fixture. | Test database spins up and tears down cleanly. | Pass |
| **Police API Integration** | Fetch recent data from the Police API client. | Successfully maps external JSON response to internal schema. | Pass |
| **Live Routes E2E** | Request A-to-B navigation via the main endpoint. | Returns fully mapped and scored route geometry `200 OK`. | Pass |
| **Worker Jobs** | Execute background data sync task. | Task completes and updates database without blocking main thread. | Pass |


## Evidence of Completion
*All test files are located in the `/tests` directory.*
*A full coverage report has been generated and is available in the repository root as `coverage_report.txt`.*