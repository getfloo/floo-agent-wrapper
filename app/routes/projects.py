import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, Request

from app.errors import APIError, error
from app.floo import Connection, FlooApp, FlooClient, Identity
from app.github import GitHubClient
from app.schemas import (
    CommitRequest,
    CommitResponse,
    CreateProject,
    DirectoryEntry,
    FileContent,
    GitToken,
    Project,
    validate_path,
)
from app.settings import Settings

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@dataclass
class Context:
    floo: FlooClient
    github: GitHubClient
    settings: Settings
    identity: Identity

    def require_write(self) -> None:
        if self.identity.effective_scope not in {"write", "admin"}:
            raise error(403, "INSUFFICIENT_KEY_SCOPE", "This action requires write scope.")

    def managed_repo(self, connection: Connection) -> str | None:
        repo = connection.repo_full_name
        if (
            connection.connected
            and repo
            and repo.startswith(f"{self.settings.github_managed_org}/")
            and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            and repo.split("/")[1] not in {".", ".."}
        ):
            return repo
        return None

    async def project_connection(self, app_id: UUID) -> tuple[str, str]:
        # Both checks use the caller's credentials on every request. A UUID
        # alone never authorizes access to a managed installation credential.
        await self.floo.get_app(app_id)
        connection = await self.floo.connection(app_id)
        repo = self.managed_repo(connection)
        if repo is None:
            raise error(404, "PROJECT_NOT_FOUND", "App has no managed repository connection.")
        return repo, connection.default_branch or "main"


async def context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_floo_org_id: Annotated[str | None, Header()] = None,
) -> AsyncIterator[Context]:
    if not authorization or not authorization.startswith("Bearer floo_"):
        raise error(401, "UNAUTHORIZED", "Missing or invalid floo API key.")
    settings = request.app.state.settings
    headers = {"Authorization": authorization}
    if x_floo_org_id is not None:
        headers["X-Floo-Org-Id"] = x_floo_org_id
    # Request-local clients prevent cookies or authorization state crossing callers.
    async with (
        httpx.AsyncClient(
            base_url=str(settings.floo_api_url), headers=headers, timeout=30
        ) as floo_http,
        httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=30,
            headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        ) as github_http,
    ):
        floo = FlooClient(floo_http)
        identity = await floo.authenticate()
        yield Context(floo, GitHubClient(github_http, settings), settings, identity)


CurrentContext = Annotated[Context, Depends(context)]


def project(app: FlooApp, repo: str, branch: str) -> Project:
    return Project(
        app_id=app.id,
        name=app.name,
        app_url=app.url,
        clone_url=f"https://github.com/{repo}.git",
        repo_full_name=repo,
        default_branch=branch,
    )


@router.post("", response_model=Project, status_code=201)
async def create_project(body: CreateProject, ctx: CurrentContext) -> Project:
    ctx.require_write()
    app = await ctx.floo.create_app(body.name)
    repo = await ctx.github.generate_repository(f"{app.name}-{app.id.hex[:8]}")
    try:
        await ctx.floo.connect(app.id, repo.full_name, repo.default_branch)
    except APIError as exc:
        # Preserve the upstream status, message and extra fields; only extend hint.
        hint = (
            f"Created app_id={app.id}, repo_id={repo.id}, repo_full_name={repo.full_name}. "
            f"Retry POST /v1/apps/{app.id}/github/connection on floo with "
            f"repo_full_name={repo.full_name} and default_branch={repo.default_branch}."
        )
        if isinstance(exc.body, dict) and isinstance(exc.body.get("detail"), dict):
            detail = exc.body["detail"]
            detail["hint"] = f"{detail['hint']} {hint}" if detail.get("hint") else hint
        else:
            exc.body = {"detail": {"code": "FLOO_ERROR", "message": exc.body, "hint": hint}}
        raise
    return project(app, repo.full_name, repo.default_branch).model_copy(
        update={"clone_url": repo.clone_url}
    )


@router.get("", response_model=list[Project])
async def list_projects(ctx: CurrentContext) -> list[Project]:
    projects = []
    for app in await ctx.floo.list_apps():
        try:
            connection = await ctx.floo.connection(app.id)
        except APIError as exc:
            if exc.status == 404:
                continue
            raise
        repo = ctx.managed_repo(connection)
        if repo:
            projects.append(project(app, repo, connection.default_branch or "main"))
    return projects


@router.get("/{app_id}/files", response_model=list[DirectoryEntry] | FileContent)
@router.get("/{app_id}/files/{path:path}", response_model=list[DirectoryEntry] | FileContent)
async def read_files(
    app_id: UUID, ctx: CurrentContext, path: str = "", ref: str | None = None
) -> list[DirectoryEntry] | FileContent:
    if path:
        try:
            validate_path(path)
        except ValueError as exc:
            raise error(422, "INVALID_PATH", str(exc)) from exc
    repo, branch = await ctx.project_connection(app_id)
    token = await ctx.github.installation_token(repo.split("/")[1])
    return await ctx.github.read(repo, path, ref if ref is not None else branch, token.token)


@router.put("/{app_id}/files", response_model=CommitResponse)
async def commit_files(app_id: UUID, body: CommitRequest, ctx: CurrentContext) -> CommitResponse:
    ctx.require_write()
    repo, branch = await ctx.project_connection(app_id)
    token = await ctx.github.installation_token(repo.split("/")[1])
    return await ctx.github.commit(repo, branch, body, token.token)


@router.post("/{app_id}/git-token", response_model=GitToken)
async def git_token(app_id: UUID, ctx: CurrentContext) -> GitToken:
    ctx.require_write()
    repo, _ = await ctx.project_connection(app_id)
    token = await ctx.github.installation_token(repo.split("/")[1])
    return GitToken(**token.model_dump(), clone_url=f"https://github.com/{repo}.git")
