from datetime import UTC, datetime

from psycopg.rows import DictRow
from psycopg_pool import ConnectionPool

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildRecord,
    BuildStatus,
    ChatMessage,
    ProcessingStatus,
)


class BuildRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def save_received(
        self,
        build: BuildIngest,
        processing_status: ProcessingStatus,
        max_log_characters: int,
    ) -> int:
        now = datetime.now(UTC)
        log = build.log[-max_log_characters:]
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO builds (
                    job_name, build_number, status, build_url, log,
                    processing_status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_name, build_number) DO UPDATE SET
                    status = EXCLUDED.status,
                    build_url = EXCLUDED.build_url,
                    log = EXCLUDED.log,
                    processing_status = EXCLUDED.processing_status,
                    category = NULL,
                    root_cause = NULL,
                    confidence = NULL,
                    recommendation = NULL,
                    error = NULL,
                    matched_known_error_id = NULL,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                (
                    build.job_name,
                    build.build_number,
                    build.status.value,
                    build.build_url,
                    log,
                    processing_status.value,
                    now,
                    now,
                ),
            ).fetchone()
        return int(row["id"])

    def mark_processing(self, build_id: int) -> None:
        self._update_status(build_id, ProcessingStatus.PROCESSING)

    def complete_success(self, build_id: int) -> None:
        self.complete_without_analysis(
            build_id,
            category="éxito",
            root_cause="La ejecución terminó correctamente.",
            recommendation="No se requiere ninguna acción.",
        )

    def complete_without_analysis(
        self,
        build_id: int,
        category: str,
        root_cause: str,
        recommendation: str,
    ) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = %s,
                    category = %s,
                    root_cause = %s,
                    confidence = 1,
                    recommendation = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    ProcessingStatus.COMPLETED.value,
                    category,
                    root_cause,
                    recommendation,
                    now,
                    build_id,
                ),
            )

    def complete_analysis(
        self,
        build_id: int,
        analysis: BuildAnalysis,
        matched_known_error_id: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = %s,
                    category = %s,
                    root_cause = %s,
                    confidence = %s,
                    recommendation = %s,
                    error = NULL,
                    matched_known_error_id = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    ProcessingStatus.COMPLETED.value,
                    analysis.category,
                    analysis.root_cause,
                    analysis.confidence,
                    analysis.recommendation,
                    matched_known_error_id,
                    now,
                    build_id,
                ),
            )

    def fail(self, build_id: int, error: str) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = %s,
                    error = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (ProcessingStatus.FAILED.value, error, now, build_id),
            )

    def get_log(self, build_id: int) -> str:
        with self.pool.connection() as connection:
            row = connection.execute(
                "SELECT log FROM builds WHERE id = %s",
                (build_id,),
            ).fetchone()
        if row is None:
            raise KeyError(build_id)
        return str(row["log"])

    def get(self, build_id: int) -> BuildRecord | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                "SELECT * FROM builds WHERE id = %s",
                (build_id,),
            ).fetchone()
        return self._to_record(row) if row else None

    def exists(self, job_name: str, build_number: int) -> bool:
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM builds
                WHERE job_name = %s AND build_number = %s
                """,
                (job_name, build_number),
            ).fetchone()
        return row is not None

    def get_last_observed_build(self, job_name: str) -> int | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                SELECT last_build_number FROM monitor_state
                WHERE job_name = %s
                """,
                (job_name,),
            ).fetchone()
        return int(row["last_build_number"]) if row else None

    def mark_build_observed(self, job_name: str, build_number: int) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state (
                    job_name, last_build_number, updated_at
                ) VALUES (%s, %s, %s)
                ON CONFLICT (job_name) DO UPDATE SET
                    last_build_number = GREATEST(
                        monitor_state.last_build_number,
                        EXCLUDED.last_build_number
                    ),
                    updated_at = EXCLUDED.updated_at
                """,
                (job_name, build_number, now),
            )

    def clear_builds(self) -> int:
        with self.pool.connection() as connection:
            cursor = connection.execute("DELETE FROM builds")
        return cursor.rowcount

    def list_recent(self, limit: int = 100) -> list[BuildRecord]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM builds
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [self._to_record(row) for row in rows]

    def list_pending(self) -> list[tuple[int, BuildStatus]]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, status FROM builds
                WHERE processing_status IN (%s, %s)
                ORDER BY created_at DESC
                """,
                (
                    ProcessingStatus.QUEUED.value,
                    ProcessingStatus.PROCESSING.value,
                ),
            ).fetchall()
        return [
            (int(row["id"]), BuildStatus(row["status"]))
            for row in rows
        ]

    def rate(self, build_id: int, rating: int, comment: str | None) -> bool:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE builds SET
                    rating = %s,
                    feedback_comment = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (rating, comment, now, build_id),
            )
        return cursor.rowcount > 0

    def add_chat_message(self, build_id: int, role: str, content: str) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO build_chat_messages (build_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (build_id, role, content, now),
            )

    def list_chat_messages(self, build_id: int) -> list[ChatMessage]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT role, content FROM build_chat_messages
                WHERE build_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (build_id,),
            ).fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]

    def _update_status(
        self,
        build_id: int,
        processing_status: ProcessingStatus,
    ) -> None:
        now = datetime.now(UTC)
        with self.pool.connection() as connection:
            connection.execute(
                """
                UPDATE builds
                SET processing_status = %s, updated_at = %s
                WHERE id = %s
                """,
                (processing_status.value, now, build_id),
            )

    @staticmethod
    def _to_record(row: DictRow) -> BuildRecord:
        return BuildRecord.model_validate(dict(row))
