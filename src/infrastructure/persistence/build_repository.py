import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src.application.models import (
    BuildAnalysis,
    BuildIngest,
    BuildRecord,
    BuildStatus,
    ProcessingStatus,
)


class BuildRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS builds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    build_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    build_url TEXT,
                    log TEXT NOT NULL,
                    processing_status TEXT NOT NULL,
                    category TEXT,
                    root_cause TEXT,
                    confidence REAL,
                    recommendation TEXT,
                    error TEXT,
                    rating INTEGER,
                    feedback_comment TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(job_name, build_number)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_state (
                    job_name TEXT PRIMARY KEY,
                    last_build_number INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_received(
        self,
        build: BuildIngest,
        processing_status: ProcessingStatus,
        max_log_characters: int,
    ) -> int:
        now = datetime.now(UTC).isoformat()
        log = build.log[-max_log_characters:]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO builds (
                    job_name, build_number, status, build_url, log,
                    processing_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_name, build_number) DO UPDATE SET
                    status = excluded.status,
                    build_url = excluded.build_url,
                    log = excluded.log,
                    processing_status = excluded.processing_status,
                    category = NULL,
                    root_cause = NULL,
                    confidence = NULL,
                    recommendation = NULL,
                    error = NULL,
                    updated_at = excluded.updated_at
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
            )
            row = connection.execute(
                """
                SELECT id FROM builds
                WHERE job_name = ? AND build_number = ?
                """,
                (build.job_name, build.build_number),
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
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = ?,
                    category = ?,
                    root_cause = ?,
                    confidence = 1,
                    recommendation = ?,
                    updated_at = ?
                WHERE id = ?
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
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = ?,
                    category = ?,
                    root_cause = ?,
                    confidence = ?,
                    recommendation = ?,
                    error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    ProcessingStatus.COMPLETED.value,
                    analysis.category,
                    analysis.root_cause,
                    analysis.confidence,
                    analysis.recommendation,
                    now,
                    build_id,
                ),
            )

    def fail(self, build_id: int, error: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE builds SET
                    processing_status = ?,
                    error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (ProcessingStatus.FAILED.value, error, now, build_id),
            )

    def get_log(self, build_id: int) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT log FROM builds WHERE id = ?",
                (build_id,),
            ).fetchone()
        if row is None:
            raise KeyError(build_id)
        return str(row["log"])

    def get(self, build_id: int) -> BuildRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM builds WHERE id = ?",
                (build_id,),
            ).fetchone()
        return self._to_record(row) if row else None

    def exists(self, job_name: str, build_number: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM builds
                WHERE job_name = ? AND build_number = ?
                """,
                (job_name, build_number),
            ).fetchone()
        return row is not None

    def get_last_observed_build(self, job_name: str) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT last_build_number FROM monitor_state
                WHERE job_name = ?
                """,
                (job_name,),
            ).fetchone()
        return int(row["last_build_number"]) if row else None

    def mark_build_observed(self, job_name: str, build_number: int) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state (
                    job_name, last_build_number, updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    last_build_number = MAX(
                        monitor_state.last_build_number,
                        excluded.last_build_number
                    ),
                    updated_at = excluded.updated_at
                """,
                (job_name, build_number, now),
            )

    def clear_builds(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM builds")
        return cursor.rowcount

    def list_recent(self, limit: int = 100) -> list[BuildRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM builds
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._to_record(row) for row in rows]

    def list_pending(self) -> list[tuple[int, BuildStatus]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, status FROM builds
                WHERE processing_status IN (?, ?)
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
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE builds SET
                    rating = ?,
                    feedback_comment = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (rating, comment, now, build_id),
            )
        return cursor.rowcount > 0

    def _update_status(
        self,
        build_id: int,
        processing_status: ProcessingStatus,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE builds
                SET processing_status = ?, updated_at = ?
                WHERE id = ?
                """,
                (processing_status.value, now, build_id),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _to_record(row: sqlite3.Row) -> BuildRecord:
        return BuildRecord.model_validate(dict(row))
