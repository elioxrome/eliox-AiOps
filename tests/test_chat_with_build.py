import pytest

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildStatus,
    ChatMessage,
    ProcessingStatus,
)
from src.application.use_cases.chat_with_build import ChatWithBuildUseCase
from src.infrastructure.persistence.build_repository import BuildRepository


class FakeChatClient:
    def __init__(self, reply: str = "It failed because of X") -> None:
        self.reply = reply
        self.received: list[ChatMessage] | None = None

    def chat(self, messages: list[ChatMessage]) -> str:
        self.received = messages
        return self.reply


def _make_analyzed_build(repository: BuildRepository) -> int:
    build_id = repository.save_received(
        BuildIngest(
            job_name="app",
            build_number=1,
            status=BuildStatus.FAILURE,
            log="boom: disk full",
        ),
        ProcessingStatus.QUEUED,
        1_000,
    )
    repository.complete_analysis(
        build_id,
        BuildAnalysis(
            category="disk",
            root_cause="disk full",
            confidence=0.9,
            recommendation="free space",
        ),
    )
    return build_id


def test_ask_persists_and_returns_conversation(repository: BuildRepository) -> None:
    build_id = _make_analyzed_build(repository)
    chat_client = FakeChatClient("Revisa el espacio en disco")
    use_case = ChatWithBuildUseCase(repository, chat_client, 1_000)

    messages = use_case.ask(build_id, "¿por qué falló?")

    assert [m.content for m in messages] == [
        "¿por qué falló?",
        "Revisa el espacio en disco",
    ]
    assert chat_client.received is not None
    assert chat_client.received[0].role == "system"
    assert "boom: disk full" in chat_client.received[0].content
    assert chat_client.received[-1] == ChatMessage(
        role="user", content="¿por qué falló?"
    )

    history = use_case.history(build_id)
    assert [m.content for m in history] == [
        "¿por qué falló?",
        "Revisa el espacio en disco",
    ]


def test_ask_unknown_build_raises_key_error(repository: BuildRepository) -> None:
    use_case = ChatWithBuildUseCase(repository, FakeChatClient(), 1_000)

    with pytest.raises(KeyError):
        use_case.ask(999, "hola")


def test_history_unknown_build_raises_key_error(
    repository: BuildRepository,
) -> None:
    use_case = ChatWithBuildUseCase(repository, FakeChatClient(), 1_000)

    with pytest.raises(KeyError):
        use_case.history(999)
