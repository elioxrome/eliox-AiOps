import re

_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?"
)
_BUILD_NUMBER_PATTERN = re.compile(r"#\d+")
_PATH_PATTERN = re.compile(r"(/[\w.\-]+){2,}")
_HEX_ID_PATTERN = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_log_signature(log: str, max_characters: int = 2_000) -> str:
    """Reduce a log tail to a stable "signature" for embedding.

    Strips timestamps, build numbers, filesystem paths and hex IDs (commit
    SHAs, container IDs) so that near-duplicate failures of the same
    underlying error produce close embeddings instead of drifting apart due
    to per-run noise.
    """
    tail = log[-max_characters:]
    normalized = _TIMESTAMP_PATTERN.sub("<ts>", tail)
    normalized = _BUILD_NUMBER_PATTERN.sub("#<n>", normalized)
    normalized = _PATH_PATTERN.sub("<path>", normalized)
    normalized = _HEX_ID_PATTERN.sub("<hex>", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()
