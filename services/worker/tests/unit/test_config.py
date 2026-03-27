import pytest
from worker.config import WorkerSettings
from pydantic import ValidationError

def test_worker_settings_validation(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WORKER_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("WORKER_API_BASE_URL", "http://api:8000")
    monkeypatch.setenv("WORKER_NOTIFICATION_BATCH_SIZE", "50")
    
    settings = WorkerSettings()
    assert settings.environment == "test"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.api_base_url == "http://api:8000"
    assert settings.notification_batch_size == 50

def test_worker_settings_missing_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("WORKER_REDIS_URL", raising=False)
    monkeypatch.delenv("WORKER_API_BASE_URL", raising=False)
    monkeypatch.delenv("WORKER_NOTIFICATION_BATCH_SIZE", raising=False)
    
    # Force pydantic to not look at any .env files
    from pydantic_settings import SettingsConfigDict
    monkeypatch.setattr(WorkerSettings, "model_config", SettingsConfigDict(env_file=None))
    
    with pytest.raises(ValidationError):
        WorkerSettings()
