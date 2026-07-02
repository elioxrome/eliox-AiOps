from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from apps.api.dependencies import get_chat_use_case
from src.application.errors import ExternalServiceError
from src.application.models import ChatTurnRequest, ChatTurnResponse
from src.application.use_cases.chat_with_build import ChatWithBuildUseCase

router = APIRouter(prefix="/api/builds", tags=["chat"])


@router.get("/{build_id}/chat", response_model=ChatTurnResponse)
def get_chat_history(
    build_id: Annotated[int, Path(ge=1)],
    use_case: Annotated[ChatWithBuildUseCase, Depends(get_chat_use_case)],
) -> ChatTurnResponse:
    try:
        return ChatTurnResponse(messages=use_case.history(build_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Build not found") from exc


@router.post("/{build_id}/chat", response_model=ChatTurnResponse)
def post_chat_message(
    build_id: Annotated[int, Path(ge=1)],
    turn: ChatTurnRequest,
    use_case: Annotated[ChatWithBuildUseCase, Depends(get_chat_use_case)],
) -> ChatTurnResponse:
    try:
        return ChatTurnResponse(messages=use_case.ask(build_id, turn.message))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Build not found") from exc
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
