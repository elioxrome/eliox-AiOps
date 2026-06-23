from urllib.parse import quote

from jenkins import Jenkins, JenkinsException
from requests import RequestException

from src.application.errors import ExternalServiceError
from src.application.models import BuildIngest, BuildStatus


class JenkinsClient:
    def __init__(
        self,
        url: str,
        username: str | None = None,
        token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.client = Jenkins(
            self.url,
            username=username,
            password=token,
            timeout=timeout_seconds,
        )

    def get_build_log(self, job_name: str, build_number: int) -> str:
        try:
            return self.client.get_build_console_output(job_name, build_number)
        except (JenkinsException, RequestException) as exc:
            raise ExternalServiceError(
                f"Could not retrieve Jenkins build {job_name} #{build_number}"
            ) from exc

    def list_latest_completed_builds(
        self,
        included_jobs: tuple[str, ...] = ("*",),
    ) -> list[BuildIngest]:
        include_all = "*" in included_jobs
        builds: list[BuildIngest] = []
        try:
            jobs = self.client.get_all_jobs()
            for job in jobs:
                job_name = job.get("fullname") or job.get("name")
                if not isinstance(job_name, str):
                    continue
                if not include_all and job_name not in included_jobs:
                    continue

                job_info = self.client.get_job_info(job_name)
                last_build = job_info.get("lastBuild")
                if not last_build:
                    continue

                build_number = last_build.get("number")
                if not isinstance(build_number, int):
                    continue
                build_info = self.client.get_build_info(job_name, build_number)
                if build_info.get("building"):
                    continue

                result = build_info.get("result")
                try:
                    build_status = BuildStatus(result)
                except (ValueError, TypeError):
                    continue

                builds.append(
                    BuildIngest(
                        job_name=job_name,
                        build_number=build_number,
                        status=build_status,
                        build_url=self._build_url(job_name, build_number),
                        log=self.get_build_log(job_name, build_number),
                    )
                )
        except (JenkinsException, RequestException) as exc:
            raise ExternalServiceError("Could not poll Jenkins jobs") from exc
        return builds

    def _build_url(self, job_name: str, build_number: int) -> str:
        job_path = "/job/".join(
            quote(segment, safe="") for segment in job_name.split("/")
        )
        return f"{self.url}/job/{job_path}/{build_number}/"
