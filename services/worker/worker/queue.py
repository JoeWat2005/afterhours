from arq.connections import RedisSettings
from arq.cron import cron

from worker.config import get_settings
from worker.jobs import ingest_transport_feeds, schedule_notifications

settings = get_settings()


class WorkerSettings:
    functions = [ingest_transport_feeds, schedule_notifications]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [
        cron(ingest_transport_feeds, minute=0),
        cron(schedule_notifications, minute={5, 20, 35, 50}),
    ]
    job_timeout = 300
    max_jobs = 10
