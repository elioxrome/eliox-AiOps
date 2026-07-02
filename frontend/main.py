from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from frontend.client import BackendClient, BackendError, BackendNotFoundError
from frontend.config import FrontendSettings
from frontend.pages import build_detail_page, dashboard_page


@lru_cache
def get_settings() -> FrontendSettings:
    return FrontendSettings.from_env()


@lru_cache
def get_backend_client() -> BackendClient:
    settings = get_settings()
    return BackendClient(settings.api_base_url, settings.request_timeout_seconds)


def _call[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except BackendNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Build not found") from exc
    except BackendError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


class FeedbackBody(BaseModel):
    rating: int
    comment: str | None = None


class ChatBody(BaseModel):
    message: str


app = FastAPI(
    title="Jenkins AIOps Frontend",
    version="0.1.0",
    description="Server-rendered dashboard; talks to the API over HTTP only.",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    settings: Annotated[FrontendSettings, Depends(get_settings)],
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> HTMLResponse:
    builds = _call(lambda: client.list_builds(settings.dashboard_limit))
    return HTMLResponse(dashboard_page(builds))


@app.get("/dashboard/builds/{build_id}", response_class=HTMLResponse)
def build_detail(
    build_id: int,
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> HTMLResponse:
    build = _call(lambda: client.get_build(build_id))
    if build is None:
        return HTMLResponse("Build not found", status_code=404)
    log = _call(lambda: client.get_log(build_id))
    return HTMLResponse(build_detail_page(build, log))


@app.get("/api/builds/{build_id}/log")
def get_log(
    build_id: int,
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> dict:
    return {"log": _call(lambda: client.get_log(build_id))}


@app.post("/api/builds/{build_id}/feedback")
def post_feedback(
    build_id: int,
    body: FeedbackBody,
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> dict:
    return _call(lambda: client.rate_build(build_id, body.rating, body.comment))


@app.get("/api/builds/{build_id}/chat")
def get_chat(
    build_id: int,
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> dict:
    return _call(lambda: client.get_chat_history(build_id))


@app.post("/api/builds/{build_id}/chat")
def post_chat(
    build_id: int,
    body: ChatBody,
    client: Annotated[BackendClient, Depends(get_backend_client)],
) -> dict:
    return _call(lambda: client.post_chat_message(build_id, body.message))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
