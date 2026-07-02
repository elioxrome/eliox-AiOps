from src.application.log_normalization import normalize_log_signature


def test_strips_timestamps_build_numbers_and_paths() -> None:
    log = (
        "2026-07-02T10:15:30.123Z Build #482 failed\n"
        "at /home/jenkins/workspace/app/src/main.py line 42\n"
        "commit a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4"
    )

    normalized = normalize_log_signature(log)

    assert "2026-07-02" not in normalized
    assert "#482" not in normalized
    assert "/home/jenkins/workspace/app/src/main.py" not in normalized
    assert "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4" not in normalized


def test_near_duplicate_logs_normalize_to_the_same_signature() -> None:
    first = "2026-07-02T10:15:30Z Build #482 failed: connection refused"
    second = "2026-07-03T11:20:05Z Build #501 failed: connection refused"

    assert normalize_log_signature(first) == normalize_log_signature(second)


def test_different_failures_normalize_differently() -> None:
    first = "connection refused"
    second = "permission denied"

    assert normalize_log_signature(first) != normalize_log_signature(second)
