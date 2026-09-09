from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel

from app.errors import APIError, error


class Identity(BaseModel):
    user_id: str
    effective_scope: str | None


class FlooApp(BaseModel):
    id: UUID
    name: str
    url: str | None


class AppPage(BaseModel):
    apps: list[FlooApp]
    total: int
    page: int
    per_page: int


class Connection(BaseModel):
    repo_full_name: str | None = None
    default_branch: str | None = None
    connected: bool = True


class FlooClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def request(self, method: str, path: str, *, auth: bool = False, **kwargs: Any) -> Any:
        try:
            response = await self.http.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise error(502, "FLOO_UNAVAILABLE", "Could not reach floo.") from exc
        if not response.is_success:
            try:
                body = response.json()
            except ValueError:
                body = {"detail": {"code": "FLOO_ERROR", "message": response.text}}
            raise APIError(401 if auth else response.status_code, body)
        return response.json()

    async def authenticate(self) -> Identity:
        return Identity.model_validate(await self.request("GET", "/v1/auth/whoami", auth=True))

    async def create_app(self, name: str) -> FlooApp:
        return FlooApp.model_validate(await self.request("POST", "/v1/apps", json={"name": name}))

    async def get_app(self, app_id: UUID) -> FlooApp:
        return FlooApp.model_validate(await self.request("GET", f"/v1/apps/{app_id}"))

    async def list_apps(self) -> list[FlooApp]:
        apps: list[FlooApp] = []
        page = 1
        while True:
            result = AppPage.model_validate(
                await self.request("GET", "/v1/apps", params={"page": page, "per_page": 100})
            )
            apps.extend(result.apps)
            if len(apps) >= result.total or not result.apps:
                return apps
            page += 1

    async def connection(self, app_id: UUID) -> Connection:
        return Connection.model_validate(
            await self.request("GET", f"/v1/apps/{app_id}/github/connection")
        )

    async def connect(self, app_id: UUID, repo: str, branch: str) -> Connection:
        return Connection.model_validate(
            await self.request(
                "POST",
                f"/v1/apps/{app_id}/github/connection",
                json={"repo_full_name": repo, "default_branch": branch},
            )
        )
