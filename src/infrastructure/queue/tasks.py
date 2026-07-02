from src.application.errors import ExternalServiceError
from src.application.models import BuildStatus
from src.infrastructure import bootstrap
from src.infrastructure.queue.celery_app import celery_app


@celery_app.task(
    name="analyze_build",
    autoretry_for=(ExternalServiceError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def analyze_build_task(build_id: int, status_value: str) -> None:
    use_case = bootstrap.get_ingest_use_case()
    use_case.process(build_id, BuildStatus(status_value))
