# How to test database models

# What is tested
This tests the database models:
- AppUser
- SafetyReport
- Journey

# How to run
Run this command from the project root:
pytest services/api/tests/test_database_models.py

# Expected result
3 passed

# Notes
- These are unit tests (no real database is used)
- Safe to run locally