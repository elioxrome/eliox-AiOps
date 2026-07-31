from datetime import date

import requests


class BackendError(RuntimeError):
    """Raised when the Jenkins AIOps API cannot fulfill a request."""


class BackendNotFoundError(BackendError):
    """Raised when the API responds 404 for a resource."""


class BackendClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def list_builds(
        self,
        limit: int,
        status: str | None = None,
        job_name: str | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        params: dict[str, str | int] = {"limit": limit}
        if status:
            params["status"] = status
        if job_name:
            params["job_name"] = job_name
        if category:
            params["category"] = category
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return self._get("/api/builds", params=params)

    def get_facets(self) -> dict:
        return self._get("/api/builds/facets")

    def get_job_summaries(self) -> list[dict]:
        return self._get("/api/builds/jobs")

    def get_build(self, build_id: int) -> dict | None:
        try:
            return self._get(f"/api/builds/{build_id}")
        except BackendNotFoundError:
            return None

    def get_log(self, build_id: int) -> str:
        payload = self._get(f"/api/builds/{build_id}/log")
        return str(payload["log"])

    def rate_build(self, build_id: int, rating: int, comment: str | None) -> dict:
        return self._post(
            f"/api/builds/{build_id}/feedback",
            json={"rating": rating, "comment": comment},
        )

    def get_chat_history(self, build_id: int) -> dict:
        return self._get(f"/api/builds/{build_id}/chat")

    def post_chat_message(self, build_id: int, message: str) -> dict:
        return self._post(
            f"/api/builds/{build_id}/chat",
            json={"message": message},
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: dict) -> dict:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise BackendError(
                f"Could not reach the API at {self.base_url}"
            ) from exc

        if response.status_code == 404:
            raise BackendNotFoundError(f"{path} not found")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise BackendError(
                f"API request to {path} failed with {response.status_code}"
            ) from exc

        return response.json()
