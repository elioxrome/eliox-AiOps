from src.application.failure_rules import detect_known_failure


def test_detects_declarative_pipeline_syntax_error() -> None:
    log = """
WorkflowScript: 14: Expected a step @ line 14, column 17.
                   irfkjvdmdfjkmd
                   ^
Finished: FAILURE
"""

    analysis = detect_known_failure(log)

    assert analysis is not None
    assert analysis.category == "sintaxis_pipeline"
    assert "línea 14" in analysis.root_cause
    assert analysis.confidence == 1
