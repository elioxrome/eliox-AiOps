from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from apps.api.dependencies import get_ollama_client, get_settings
from src.application.errors import ExternalServiceError
from src.application.models import BuildAnalysis
from src.application.use_cases.analyze_build import AnalyzeBuildUseCase
from src.config import Settings
from src.infrastructure.jenkins.client import JenkinsClient

router = APIRouter(prefix="/analyze", tags=["analysis"])


def get_analyze_build_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalyzeBuildUseCase:
    jenkins = JenkinsClient(
        settings.jenkins_url,
        settings.jenkins_username,
        settings.jenkins_token,
        settings.jenkins_timeout_seconds,
    )
    llm = get_ollama_client()
    return AnalyzeBuildUseCase(jenkins, llm, settings.max_log_characters)


@router.get("/{job}/{build}", response_model=BuildAnalysis)
def analyze(
    job: Annotated[str, Path(min_length=1)],
    build: Annotated[int, Path(ge=1)],
    use_case: Annotated[
        AnalyzeBuildUseCase, Depends(get_analyze_build_use_case)
    ],
) -> BuildAnalysis:
    try:
        return use_case.execute(job, build)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
