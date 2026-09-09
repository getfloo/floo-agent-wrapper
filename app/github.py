import base64
import binascii
import time
from typing import Any
from urllib.parse import quote

import httpx
import jwt
from pydantic import BaseModel

from app.errors import APIError, error
from app.schemas import CommitRequest, CommitResponse, DirectoryEntry, FileContent
from app.settings import Settings


class InstallationToken(BaseModel):
    token: str
    expires_at: str


class Repository(BaseModel):
    id: int
    full_name: str
    clone_url: str
    default_branch: str


class GitHubClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings):
        self.http = http
        self.settings = settings

    def app_jwt(self) -> str:
        now = int(time.time())
        return jwt.encode(
            {"iat": now - 60, "exp": now + 9 * 60, "iss": str(self.settings.github_app_id)},
            self.settings.github_app_private_key.get_secret_value(),
            algorithm="RS256",
        )

    async def request(self, method: str, path: str, token: str, **kwargs: Any) -> Any:
        try:
            response = await self.http.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
        except httpx.RequestError as exc:
            raise error(502, "GITHUB_UNAVAILABLE", "Could not reach GitHub.") from exc
        if not response.is_success:
            try:
                message = response.json().get("message", "GitHub request failed.")
            except ValueError:
                message = "GitHub request failed."
            raise error(
                response.status_code if 400 <= response.status_code < 500 else 502,
                "GITHUB_ERROR",
                message,
            )
        return response.json()

    async def installation_token(self, repo_name: str) -> InstallationToken:
        return InstallationToken.model_validate(
            await self.request(
                "POST",
                f"/app/installations/{self.settings.github_installation_id}/access_tokens",
                self.app_jwt(),
                json={
                    "repositories": [repo_name],
                    "permissions": {"contents": "write", "metadata": "read"},
                },
            )
        )

    async def generate_repository(self, name: str) -> Repository:
        # A nonexistent repo cannot be included in a scoped token. This internal,
        # creation-only credential is never returned to the caller or cached.
        token = InstallationToken.model_validate(
            await self.request(
                "POST",
                f"/app/installations/{self.settings.github_installation_id}/access_tokens",
                self.app_jwt(),
                json={
                    "permissions": {
                        "administration": "write",
                        "contents": "write",
                        "metadata": "read",
                    }
                },
            )
        )
        return Repository.model_validate(
            await self.request(
                "POST",
                f"/repos/{self.settings.github_template_repo}/generate",
                token.token,
                json={"owner": self.settings.github_managed_org, "name": name, "private": True},
            )
        )

    async def read(
        self, repo: str, path: str, ref: str, token: str
    ) -> list[DirectoryEntry] | FileContent:
        result = await self.request(
            "GET", f"/repos/{repo}/contents/{quote(path, safe='/')}", token, params={"ref": ref}
        )
        if isinstance(result, list):
            return [DirectoryEntry.model_validate(entry) for entry in result]
        if result.get("encoding") != "base64":
            raise error(502, "UNSUPPORTED_CONTENT", "GitHub did not return base64 file content.")
        try:
            raw = base64.b64decode("".join(result["content"].split()), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise error(502, "INVALID_CONTENT", "GitHub returned invalid base64 content.") from exc
        try:
            return FileContent(
                path=result["path"],
                sha=result["sha"],
                encoding="utf-8",
                content=raw.decode("utf-8"),
            )
        except UnicodeDecodeError:
            return FileContent(
                path=result["path"],
                sha=result["sha"],
                encoding="base64",
                content=base64.b64encode(raw).decode("ascii"),
            )

    async def head(self, repo: str, branch: str, token: str) -> str:
        result = await self.request(
            "GET", f"/repos/{repo}/git/ref/heads/{quote(branch, safe='')}", token
        )
        return result["object"]["sha"]

    @staticmethod
    def conflict(current_sha: str) -> APIError:
        return error(
            409,
            "STALE_BASE_SHA",
            "The branch head has changed.",
            current_sha=current_sha,
            hint=f"Read the latest files and retry with base_sha={current_sha}.",
        )

    async def commit(
        self, repo: str, branch: str, batch: CommitRequest, token: str
    ) -> CommitResponse:
        head = await self.head(repo, branch, token)
        if head.lower() != batch.base_sha.lower():
            raise self.conflict(head)
        parent = await self.request("GET", f"/repos/{repo}/git/commits/{head}", token)
        entries = []
        for file in batch.files:
            sha = None
            if file.content is not None:
                blob = await self.request(
                    "POST",
                    f"/repos/{repo}/git/blobs",
                    token,
                    json={"content": file.content, "encoding": "utf-8"},
                )
                sha = blob["sha"]
            entries.append({"path": file.path, "mode": "100644", "type": "blob", "sha": sha})
        tree = await self.request(
            "POST",
            f"/repos/{repo}/git/trees",
            token,
            json={"base_tree": parent["tree"]["sha"], "tree": entries},
        )
        commit = await self.request(
            "POST",
            f"/repos/{repo}/git/commits",
            token,
            json={"message": batch.message, "tree": tree["sha"], "parents": [head]},
        )
        try:
            await self.request(
                "PATCH",
                f"/repos/{repo}/git/refs/heads/{quote(branch, safe='')}",
                token,
                json={"sha": commit["sha"], "force": False},
            )
        except APIError as exc:
            # Non-fast-forward updates can race the initial head check. Do not
            # retry writes; report the new head if another writer won.
            if exc.status in {409, 422}:
                current = await self.head(repo, branch, token)
                if current != head:
                    raise self.conflict(current) from exc
            raise
        return CommitResponse(commit_sha=commit["sha"], previous_sha=head)
