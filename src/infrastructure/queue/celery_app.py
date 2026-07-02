from celery import Celery

from src.config import Settings

_settings = Settings.from_env()

celery_app = Celery(
    "jenkins_aiops",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.update(
    task_default_queue="analysis",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
)
