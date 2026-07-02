from src.application.models import BuildStatus
from src.infrastructure.queue.celery_app import celery_app


class CeleryAnalysisDispatcher:
    def dispatch(self, build_id: int, status: BuildStatus) -> None:
        celery_app.send_task(
            "analyze_build",
            args=(build_id, status.value),
            queue="analysis",
        )
