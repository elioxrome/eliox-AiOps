from src.application.models import ChatMessage
from src.infrastructure.llm.base import ChatClient
from src.infrastructure.llm.prompts import CHAT_SYSTEM_PROMPT
from src.infrastructure.persistence.base import BuildRepositoryPort


class ChatWithBuildUseCase:
    def __init__(
        self,
        repository: BuildRepositoryPort,
        chat_client: ChatClient,
        max_log_characters: int,
    ) -> None:
        self.repository = repository
        self.chat_client = chat_client
        self.max_log_characters = max_log_characters

    def history(self, build_id: int) -> list[ChatMessage]:
        if self.repository.get(build_id) is None:
            raise KeyError(build_id)
        return self.repository.list_chat_messages(build_id)

    def ask(self, build_id: int, question: str) -> list[ChatMessage]:
        build = self.repository.get(build_id)
        if build is None:
            raise KeyError(build_id)

        log = self.repository.get_log(build_id)
        diagnosis = build.root_cause or "Sin diagnóstico todavía."
        system_prompt = CHAT_SYSTEM_PROMPT.format(
            status=build.status.value,
            diagnosis=diagnosis,
            log=log[-self.max_log_characters :],
        )

        history = self.repository.list_chat_messages(build_id)
        messages = [
            ChatMessage(role="system", content=system_prompt),
            *history,
            ChatMessage(role="user", content=question),
        ]
        reply = self.chat_client.chat(messages)

        self.repository.add_chat_message(build_id, "user", question)
        self.repository.add_chat_message(build_id, "assistant", reply)
        return [
            *history,
            ChatMessage(role="user", content=question),
            ChatMessage(role="assistant", content=reply),
        ]
