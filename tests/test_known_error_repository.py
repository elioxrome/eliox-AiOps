from psycopg_pool import ConnectionPool

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildStatus,
    ProcessingStatus,
)
from src.infrastructure.persistence.build_repository import BuildRepository
from src.infrastructure.persistence.known_error_repository import (
    KnownErrorRepository,
)

_ANALYSIS = BuildAnalysis(
    category="net",
    root_cause="timeout",
    confidence=0.9,
    recommendation="retry",
)
_UNIT_VECTOR = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def _make_build(repository: BuildRepository) -> int:
    return repository.save_received(
        BuildIngest(
            job_name="app",
            build_number=1,
            status=BuildStatus.FAILURE,
            log="boom",
        ),
        ProcessingStatus.QUEUED,
        1_000,
    )


def test_find_similar_returns_none_when_empty(
    known_error_repository: KnownErrorRepository,
) -> None:
    assert known_error_repository.find_similar([0.0] * 8, threshold=1.0) is None


def test_find_similar_returns_match_within_threshold(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    build_id = _make_build(repository)
    embedding = _UNIT_VECTOR
    known_error_repository.insert(
        "connection timeout", embedding, _ANALYSIS, build_id
    )

    match = known_error_repository.find_similar(embedding, threshold=0.01)

    assert match is not None
    assert match.analysis.root_cause == "timeout"
    assert match.distance == 0.0


def test_find_similar_respects_threshold(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    build_id = _make_build(repository)
    known_error_repository.insert(
        "connection timeout", _UNIT_VECTOR, _ANALYSIS, build_id
    )

    far_vector = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert known_error_repository.find_similar(far_vector, threshold=0.5) is None


def test_untrusted_entries_are_excluded(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
) -> None:
    build_id = _make_build(repository)
    known_error_id = known_error_repository.insert(
        "connection timeout", _UNIT_VECTOR, _ANALYSIS, build_id
    )
    for _ in range(5):
        known_error_repository.adjust_trust(known_error_id, rating=-1)

    assert (
        known_error_repository.find_similar(_UNIT_VECTOR, threshold=0.01) is None
    )


def test_record_hit_increments_counter(
    repository: BuildRepository,
    known_error_repository: KnownErrorRepository,
    db_pool: ConnectionPool,
) -> None:
    build_id = _make_build(repository)
    known_error_id = known_error_repository.insert(
        "connection timeout", _UNIT_VECTOR, _ANALYSIS, build_id
    )

    known_error_repository.record_hit(known_error_id)

    with db_pool.connection() as connection:
        row = connection.execute(
            "SELECT hit_count FROM known_errors WHERE id = %s",
            (known_error_id,),
        ).fetchone()
    assert row["hit_count"] == 1
