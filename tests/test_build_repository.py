from datetime import date, timedelta

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.infrastructure.persistence.build_repository import BuildRepository

_ANALYSIS = BuildAnalysis(
    category="net",
    root_cause="timeout",
    confidence=0.9,
    recommendation="retry",
    affected_file="src/app.py",
)


def _ingest(
    repository: BuildRepository,
    job_name: str,
    build_number: int,
    status: BuildStatus,
) -> int:
    return repository.save_received(
        BuildIngest(
            job_name=job_name,
            build_number=build_number,
            status=status,
            log="boom",
        ),
        ProcessingStatus.QUEUED,
        1_000,
    )


def test_complete_analysis_persists_affected_file(
    repository: BuildRepository,
) -> None:
    build_id = _ingest(repository, "app", 1, BuildStatus.FAILURE)

    repository.complete_analysis(build_id, _ANALYSIS)

    record = repository.get(build_id)
    assert record is not None
    assert record.affected_file == "src/app.py"


def test_list_recent_filters_by_status(repository: BuildRepository) -> None:
    failed = _ingest(repository, "app", 1, BuildStatus.FAILURE)
    _ingest(repository, "app", 2, BuildStatus.SUCCESS)

    results = repository.list_recent(100, status=BuildStatus.FAILURE)

    assert [record.id for record in results] == [failed]


def test_list_recent_filters_by_job_name_partial_match(
    repository: BuildRepository,
) -> None:
    backend = _ingest(repository, "backend-service", 1, BuildStatus.FAILURE)
    _ingest(repository, "frontend-app", 1, BuildStatus.FAILURE)

    results = repository.list_recent(100, job_name="backend")

    assert [record.id for record in results] == [backend]


def test_list_recent_filters_by_category(repository: BuildRepository) -> None:
    matching = _ingest(repository, "app", 1, BuildStatus.FAILURE)
    other = _ingest(repository, "app", 2, BuildStatus.FAILURE)
    repository.complete_analysis(matching, _ANALYSIS)
    repository.complete_analysis(
        other, _ANALYSIS.model_copy(update={"category": "disk"})
    )

    results = repository.list_recent(100, category="net")

    assert [record.id for record in results] == [matching]


def test_list_recent_filters_by_date_range(repository: BuildRepository) -> None:
    build_id = _ingest(repository, "app", 1, BuildStatus.FAILURE)
    today = date.today()

    in_range = repository.list_recent(
        100, date_from=today, date_to=today + timedelta(days=1)
    )
    out_of_range = repository.list_recent(
        100, date_from=today + timedelta(days=1), date_to=today + timedelta(days=2)
    )

    assert [record.id for record in in_range] == [build_id]
    assert out_of_range == []


def test_list_facets_returns_distinct_sorted_values(
    repository: BuildRepository,
) -> None:
    beta = _ingest(repository, "beta", 1, BuildStatus.FAILURE)
    _ingest(repository, "alpha", 1, BuildStatus.FAILURE)
    _ingest(repository, "alpha", 2, BuildStatus.FAILURE)
    repository.complete_analysis(beta, _ANALYSIS)

    facets = repository.list_facets()

    assert facets.jobs == ["alpha", "beta"]
    assert facets.categories == ["net"]


def test_list_job_summaries_groups_counts_by_job(
    repository: BuildRepository,
) -> None:
    _ingest(repository, "alpha", 1, BuildStatus.SUCCESS)
    _ingest(repository, "alpha", 2, BuildStatus.FAILURE)
    _ingest(repository, "alpha", 3, BuildStatus.UNSTABLE)
    _ingest(repository, "beta", 1, BuildStatus.ABORTED)

    summaries = {s.job_name: s for s in repository.list_job_summaries()}

    alpha = summaries["alpha"]
    assert alpha.total_builds == 3
    assert alpha.success_count == 1
    assert alpha.failure_count == 2
    assert alpha.other_count == 0

    beta = summaries["beta"]
    assert beta.total_builds == 1
    assert beta.success_count == 0
    assert beta.failure_count == 0
    assert beta.other_count == 1
