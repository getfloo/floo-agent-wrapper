from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateProject(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class Project(BaseModel):
    app_id: UUID
    name: str
    app_url: str | None
    clone_url: str
    repo_full_name: str
    default_branch: str


def validate_path(path: str) -> str:
    if (
        not path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or "\\" in path
        or any(ord(char) < 32 for char in path)
    ):
        raise ValueError("Path must be a relative repository path without empty, . or .. segments")
    return path


class FileChange(BaseModel):
    path: str
    content: str | None

    _validate_path = field_validator("path")(validate_path)


class CommitRequest(BaseModel):
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    message: str = Field(min_length=1)
    files: list[FileChange] = Field(min_length=1)

    @field_validator("files")
    @classmethod
    def unique_paths(cls, files: list[FileChange]) -> list[FileChange]:
        paths = [file.path for file in files]
        if len(set(paths)) != len(paths):
            raise ValueError("Each path may appear only once in a batch")
        return files


class CommitResponse(BaseModel):
    commit_sha: str
    previous_sha: str


class DirectoryEntry(BaseModel):
    path: str
    type: str
    size: int
    sha: str


class FileContent(BaseModel):
    path: str
    sha: str
    encoding: Literal["utf-8", "base64"]
    content: str


class GitToken(BaseModel):
    token: str
    expires_at: str
    clone_url: str
