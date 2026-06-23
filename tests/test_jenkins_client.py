import pytest
import requests

from src.application.errors import ExternalServiceError
from src.infrastructure.jenkins.client import JenkinsClient


class FailingJenkins:
    def get_build_console_output(
        self,
        job_name: str,
        build_number: int,
    ) -> str:
        raise requests.ConnectionError("connection refused")


def test_converts_connection_errors_to_application_error() -> None:
    client = JenkinsClient.__new__(JenkinsClient)
    client.client = FailingJenkins()

    with pytest.raises(
        ExternalServiceError,
        match=r"Could not retrieve Jenkins build deploy #42",
    ):
        client.get_build_log("deploy", 42)
