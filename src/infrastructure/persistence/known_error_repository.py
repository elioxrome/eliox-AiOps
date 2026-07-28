from datetime import UTC, datetime

from psycopg_pool import ConnectionPool

from src.application.models import BuildAnalysis
from src.infrastructure.persistence.base import KnownErrorMatch

_TRUST_FLOOR = 0.0
_TRUST_CEILING = 2.0
_TRUST_STEP = 0.25


class KnownErrorRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def find_similar(
        self,
        embedding: list[float],
        threshold: float,
    ) -> KnownErrorMatch | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                SELECT id, category, root_cause, recommendation, confidence,
                       affected_file,
                       embedding <=> %s::vector AS distance
                FROM known_errors
                WHERE trust_score > 0
                ORDER BY embedding <=> %s::vector
                LIMIT 1
                """,
                (embedding, embedding),
            ).fetchone()
        if row is None or row["distance"] > threshold:
            return None
        return KnownErrorMatch(
            id=int(row["id"]),
            analysis=BuildAnalysis(
                category=row["category"],
                root_cause=row["root_cause"],
                confidence=row["confidence"],
                recommendation=row["recommendation"],
                affected_file=row["affected_file"],
            ),
            distance=float(row["distance"]),
        )

    def record_hit(self, known_error_id: int) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE known_errors SET
                    hit_count = hit_count + 1,
                    last_matched_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (now, now, known_error_id),
            )

    def insert(
        self,
        signature: str,
        embedding: list[float],
        analysis: BuildAnalysis,
        source_build_id: int,
    ) -> int:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO known_errors (
                    signature, embedding, category, root_cause, recommendation,
                    confidence, affected_file, source_build_id, created_at,
                    updated_at
                ) VALUES (%s, %s::vector, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    signature,
                    embedding,
                    analysis.category,
                    analysis.root_cause,
                    analysis.recommendation,
                    analysis.confidence,
                    analysis.affected_file,
                    source_build_id,
                    now,
                    now,
                ),
            ).fetchone()
        return int(row["id"])

    def adjust_trust(self, known_error_id: int, rating: int) -> None:
        now = datetime.now(UTC)
        delta = _TRUST_STEP if rating > 0 else -_TRUST_STEP if rating < 0 else 0.0
        if delta == 0.0:
            return
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE known_errors SET
                    trust_score = GREATEST(%s, LEAST(%s, trust_score + %s)),
                    updated_at = %s
                WHERE id = %s
                """,
                (_TRUST_FLOOR, _TRUST_CEILING, delta, now, known_error_id),
            )
