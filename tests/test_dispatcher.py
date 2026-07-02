from unittest.mock import patch

from src.application.models import BuildStatus
from src.infrastructure.queue.dispatcher import CeleryAnalysisDispatcher


def test_dispatch_sends_a_celery_task() -> None:
    dispatcher = CeleryAnalysisDispatcher()

    with patch(
        "src.infrastructure.queue.dispatcher.celery_app.send_task"
    ) as send_task:
        dispatcher.dispatch(42, BuildStatus.FAILURE)

    send_task.assert_called_once_with(
        "analyze_build",
        args=(42, "FAILURE"),
        queue="analysis",
    )
