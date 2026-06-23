class ExternalServiceError(RuntimeError):
    """Raised when Jenkins or the configured LLM cannot fulfill a request."""


class InvalidLLMResponseError(ExternalServiceError):
    """Raised when the LLM response does not match the expected contract."""
