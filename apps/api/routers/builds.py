import hmac
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)

from apps.api.dependencies import (
    get_ingest_use_case,
    get_known_error_repository,
    get_repository,
    get_settings,
)
from src.application.models import (
    BuildAccepted,
    BuildFeedback,
    BuildIngest,
    BuildLogResponse,
    BuildRecord,
    BuildStatus,
    ClearBuildsResult,
)
from src.application.use_cases.ingest_build import IngestBuildUseCase
from src.config import Settings
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)

router = APIRouter(prefix="/api/builds", tags=["builds"])


def authorize_ingestion(
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Header(alias="X-AIOPS-Token")] = None,
) -> None:
    expected = settings.ingestion_token
    if expected and (token is None or not hmac.compare_digest(token, expected)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ingestion token",
        )


@router.post(
    "",
    response_model=BuildAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(authorize_ingestion)],
)
def ingest_build(
    build: BuildIngest,
    use_case: Annotated[IngestBuildUseCase, Depends(get_ingest_use_case)],
) -> BuildAccepted:
    build_id, processing_status = use_case.receive(build)

    message = (
        "Build registered without LLM analysis"
        if build.status not in {BuildStatus.FAILURE, BuildStatus.UNSTABLE}
        else "Build queued for analysis"
    )
    return BuildAccepted(
        id=build_id,
        processing_status=processing_status,
        message=message,
    )


@router.get("", response_model=list[BuildRecord])
def list_builds(
    repository: Annotated[BuildRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[BuildRecord]:
    return repository.list_recent(limit)


@router.delete(
    "",
    response_model=ClearBuildsResult,
    dependencies=[Depends(authorize_ingestion)],
)
def clear_builds(
    repository: Annotated[BuildRepository, Depends(get_repository)],
) -> ClearBuildsResult:
    return ClearBuildsResult(deleted=repository.clear_builds())


@router.get("/{build_id}", response_model=BuildRecord)
def get_build(
    build_id: int,
    repository: Annotated[BuildRepository, Depends(get_repository)],
) -> BuildRecord:
    record = repository.get(build_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return record


@router.get("/{build_id}/log", response_model=BuildLogResponse)
def get_build_log(
    build_id: int,
    repository: Annotated[BuildRepository, Depends(get_repository)],
) -> BuildLogResponse:
    try:
        return BuildLogResponse(log=repository.get_log(build_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Build not found") from exc


@router.post("/{build_id}/feedback", response_model=BuildRecord)
def rate_build(
    build_id: int,
    feedback: BuildFeedback,
    repository: Annotated[BuildRepository, Depends(get_repository)],
    known_errors: Annotated[
        KnownErrorRepository, Depends(get_known_error_repository)
    ],
) -> BuildRecord:
    if not repository.rate(build_id, feedback.rating, feedback.comment):
        raise HTTPException(status_code=404, detail="Build not found")
    record = repository.get(build_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Build not found")
    if record.matched_known_error_id is not None:
        known_errors.adjust_trust(record.matched_known_error_id, feedback.rating)
    return record
