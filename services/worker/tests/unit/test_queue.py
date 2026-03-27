from worker.queue import WorkerSettings as ArqWorkerSettings
from worker.jobs import ingest_transport_feeds, schedule_notifications

def test_worker_queue_settings():
    # Check that the worker settings class has the correct job functions
    assert ingest_transport_feeds in ArqWorkerSettings.functions
    assert schedule_notifications in ArqWorkerSettings.functions
    
    # Check redis settings existence
    assert ArqWorkerSettings.redis_settings is not None
    
    # Check cron jobs are defined
    assert len(ArqWorkerSettings.cron_jobs) == 2
    
    # Check job timeout and max jobs
    assert ArqWorkerSettings.job_timeout == 300
    assert ArqWorkerSettings.max_jobs == 10
