"""arq worker entrypoint.

Run with:
    arq app.workers.arq_worker.WorkerSettings

Started as a separate container (`worker` service in docker-compose).
"""
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import configure_logging
from app.services.webhook_outbound import process_webhook_delivery


configure_logging()


class WorkerSettings:
    """arq picks up class attributes by convention. See docs.aiohttp.org/arq."""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [process_webhook_delivery]

    # Reasonable defaults for our workload (sparse small jobs).
    max_jobs = 20
    job_timeout = 30
    keep_result = 60 * 60  # keep arq's job result 1 hour for inspection
    max_tries = 1  # we manage retries ourselves via WebhookDelivery + scheduling
