from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class BuildStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNSTABLE = "UNSTABLE"
    ABORTED = "ABORTED"
    NOT_BUILT = "NOT_BUILT"


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildAnalysis(BaseModel):
    category: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    recommendation: str = Field(min_length=1)
    affected_file: str | None = None


class HealthStatus(BaseModel):
    status: str


class BuildIngest(BaseModel):
    job_name: str = Field(min_length=1, max_length=500)
    build_number: int = Field(ge=1)
    status: BuildStatus
    log: str = Field(default="", max_length=1_000_000)
    build_url: str | None = Field(default=None, max_length=2_000)

    @field_validator("job_name")
    @classmethod
    def normalize_job_name(cls, value: str) -> str:
        return value.strip()


class BuildAccepted(BaseModel):
    id: int
    processing_status: ProcessingStatus
    message: str


class ClearBuildsResult(BaseModel):
    deleted: int


class BuildRecord(BaseModel):
    id: int
    job_name: str
    build_number: int
    status: BuildStatus
    build_url: str | None
    processing_status: ProcessingStatus
    category: str | None
    root_cause: str | None
    confidence: float | None
    recommendation: str | None
    affected_file: str | None
    error: str | None
    rating: int | None
    feedback_comment: str | None
    matched_known_error_id: int | None = None
    created_at: datetime
    updated_at: datetime


class BuildFeedback(BaseModel):
    rating: int = Field(ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=1_000)


class BuildLogResponse(BaseModel):
    log: str


class BuildFacets(BaseModel):
    jobs: list[str]
    categories: list[str]


class JobSummary(BaseModel):
    job_name: str
    total_builds: int
    success_count: int
    failure_count: int
    other_count: int
    last_build_at: datetime


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=4_000)


class ChatTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)


class ChatTurnResponse(BaseModel):
    messages: list[ChatMessage]
