import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.dependencies import get_jenkins_monitor, get_settings
from apps.api.routers.analysis import router
from apps.api.routers.builds import router as builds_router
from apps.api.routers.chat import router as chat_router
from src.application.models import HealthStatus
from src.infrastructure import bootstrap


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    stop_event = asyncio.Event()
    monitor_task = None
    if settings.jenkins_poll_enabled:
        monitor_task = asyncio.create_task(
            get_jenkins_monitor().run(stop_event)
        )
    yield
    stop_event.set()
    if monitor_task:
        await monitor_task
    bootstrap.get_pool().close()


app = FastAPI(
    title="Jenkins AIOps",
    version="0.3.0",
    description="Analyze Jenkins build logs with a locally hosted LLM.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(builds_router)
app.include_router(chat_router)


@app.get("/health", response_model=HealthStatus, tags=["operations"])
def health() -> HealthStatus:
    return HealthStatus(status="ok")
