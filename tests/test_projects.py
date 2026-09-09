import base64
import json
import time
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization

FLOO = "https://floo.test"
GH = "https://api.github.com"
APP_ID = "12345678-1234-1234-1234-123456789abc"
OTHER_ID = "87654321-1234-1234-1234-123456789abc"
APP = {"id": APP_ID, "name": "demo", "url": "https://demo.floo.app"}
REPO = "managed/renamed-repo"
BRANCH = "feature/work"
HEAD = "a" * 40
NEW_HEAD = "b" * 40
TOKEN_URL = f"{GH}/app/installations/456/access_tokens"
TOKEN = {"token": "repo-token", "expires_at": "2026-09-09T12:00:00Z"}
CONNECTION_URL = f"{FLOO}/v1/apps/{APP_ID}/github/connection"
BATCH = {
    "base_sha": HEAD,
    "message": "Update app",
    "files": [{"path": "main.py", "content": "print('hello')"}],
}


def authenticate(upstream, scope="write"):
    return upstream.get(f"{FLOO}/v1/auth/whoami").respond(
        200, json={"user_id": "user-id", "effective_scope": scope}
    )


def connected(upstream, repo=REPO, branch=BRANCH):
    upstream.get(f"{FLOO}/v1/apps/{APP_ID}").respond(200, json=APP)
    upstream.get(CONNECTION_URL).respond(
        200, json={"repo_full_name": repo, "default_branch": branch, "connected": True}
    )


def mint(upstream):
    return upstream.post(TOKEN_URL).respond(201, json=TOKEN)


def assert_scoped(route, repo="renamed-repo"):
    assert json.loads(route.calls.last.request.content) == {
        "repositories": [repo],
        "permissions": {"contents": "write", "metadata": "read"},
    }


def mock_create(upstream):
    authenticate(upstream)
    app = upstream.post(f"{FLOO}/v1/apps").respond(201, json=APP)
    token = mint(upstream)
    generate = upstream.post(f"{GH}/repos/templates/starter/generate").respond(
        201,
        json={
            "id": 987,
            "full_name": "managed/demo-12345678",
            "clone_url": "https://github.com/managed/demo-12345678.git",
            "default_branch": "main",
        },
    )
    return app, token, generate


async def test_health_needs_no_auth_or_upstream(client, upstream):
    client.headers.clear()
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(upstream.calls) == 0


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/v1/projects", {"name": "demo"}),
        ("GET", "/v1/projects", None),
        ("GET", f"/v1/projects/{APP_ID}/files", None),
        ("GET", f"/v1/projects/{APP_ID}/files/main.py", None),
        ("PUT", f"/v1/projects/{APP_ID}/files", BATCH),
        ("POST", f"/v1/projects/{APP_ID}/git-token", None),
    ],
)
async def test_bad_key_on_every_route(client, upstream, method, path, body):
    upstream.get(f"{FLOO}/v1/auth/whoami").respond(
        403, json={"detail": {"code": "BAD_KEY", "message": "Key revoked."}}
    )
    response = await client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Key revoked."
    assert len(upstream.calls) == 1


@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer unrelated"])
async def test_missing_or_non_floo_auth(client, upstream, header):
    client.headers.clear()
    if header is not None:
        client.headers["Authorization"] = header
    response = await client.get("/v1/projects")
    assert response.status_code == 401
    assert not upstream.calls


@pytest.mark.parametrize("status", [302, 401, 403, 500])
async def test_all_whoami_failures_map_to_401(client, upstream, status):
    upstream.get(f"{FLOO}/v1/auth/whoami").respond(status, json={"detail": {"message": "No"}})
    assert (await client.get("/v1/projects")).status_code == 401


async def test_create_project(client, upstream, private_key):
    app, token, generate = mock_create(upstream)
    connect = upstream.post(CONNECTION_URL).respond(
        200,
        json={
            "repo_full_name": "managed/demo-12345678",
            "default_branch": "main",
        },
    )
    response = await client.post("/v1/projects", json={"name": "demo"})
    assert response.status_code == 201
    assert response.json() == {
        "app_id": APP_ID,
        "name": "demo",
        "app_url": APP["url"],
        "clone_url": "https://github.com/managed/demo-12345678.git",
        "repo_full_name": "managed/demo-12345678",
        "default_branch": "main",
    }
    assert json.loads(app.calls.last.request.content) == {"name": "demo"}
    assert json.loads(generate.calls.last.request.content) == {
        "owner": "managed",
        "name": "demo-12345678",
        "private": True,
    }
    assert json.loads(connect.calls.last.request.content) == {
        "repo_full_name": "managed/demo-12345678",
        "default_branch": "main",
    }
    assert json.loads(token.calls.last.request.content) == {
        "permissions": {
            "administration": "write",
            "contents": "write",
            "metadata": "read",
        }
    }
    signed = token.calls.last.request.headers["Authorization"].removeprefix("Bearer ")
    public_key = serialization.load_pem_private_key(private_key.encode(), None).public_key()
    claims = jwt.decode(signed, public_key, algorithms=["RS256"])
    now = int(time.time())
    assert claims["iss"] == "123"
    assert abs(claims["iat"] - (now - 60)) <= 5
    assert abs(claims["exp"] - (now + 540)) <= 5
    assert generate.calls.last.request.headers["Authorization"] == "Bearer repo-token"
    for call in upstream.calls:
        if call.request.url.host == "floo.test":
            assert call.request.headers["Authorization"] == "Bearer floo_test"
            assert call.request.headers["X-Floo-Org-Id"] == "org-test"
        else:
            assert "X-Floo-Org-Id" not in call.request.headers


@pytest.mark.parametrize("status", [403, 409, 503])
async def test_connect_failure_preserves_resources_and_error(client, upstream, status):
    mock_create(upstream)
    original = {
        "code": "INSTALLATION_NOT_LINKED",
        "message": "Link installation.",
        "hint": "Choose an installation.",
        "extra_fact": "retained",
    }
    upstream.post(CONNECTION_URL).respond(status, json={"detail": original})
    response = await client.post("/v1/projects", json={"name": "demo"})
    assert response.status_code == status
    detail = response.json()["detail"]
    assert {k: v for k, v in detail.items() if k != "hint"} == {
        k: v for k, v in original.items() if k != "hint"
    }
    assert detail["hint"].startswith(original["hint"])
    assert APP_ID in detail["hint"]
    assert "repo_id=987" in detail["hint"]
    assert "managed/demo-12345678" in detail["hint"]
    assert len(upstream.calls) == 5  # No compensation or retry calls.


async def test_list_pages_filters_managed_org_and_uses_connections(client, upstream):
    authenticate(upstream)
    apps = [APP, {**APP, "id": OTHER_ID}]
    unconnected = {**APP, "id": str(UUID(int=3))}
    disconnected = {**APP, "id": str(UUID(int=4))}
    upstream.get(f"{FLOO}/v1/apps", params={"page": 1, "per_page": 100}).respond(
        200, json={"apps": apps, "total": 4, "page": 1, "per_page": 2}
    )
    second = upstream.get(f"{FLOO}/v1/apps", params={"page": 2, "per_page": 100}).respond(
        200, json={"apps": [unconnected, disconnected], "total": 4, "page": 2, "per_page": 2}
    )
    upstream.get(CONNECTION_URL).respond(
        200,
        json={
            "repo_full_name": REPO,
            "default_branch": BRANCH,
        },
    )
    upstream.get(f"{FLOO}/v1/apps/{OTHER_ID}/github/connection").respond(
        200,
        json={
            "repo_full_name": "managed-evil/demo",
            "default_branch": "main",
        },
    )
    upstream.get(f"{FLOO}/v1/apps/{unconnected['id']}/github/connection").respond(404)
    upstream.get(f"{FLOO}/v1/apps/{disconnected['id']}/github/connection").respond(
        200,
        json={
            "repo_full_name": "managed/old",
            "connected": False,
        },
    )
    response = await client.get("/v1/projects")
    assert response.status_code == 200
    assert second.called
    assert response.json() == [
        {
            "app_id": APP_ID,
            "name": "demo",
            "app_url": APP["url"],
            "clone_url": f"https://github.com/{REPO}.git",
            "repo_full_name": REPO,
            "default_branch": BRANCH,
        }
    ]
    assert all(call.request.url.host == "floo.test" for call in upstream.calls)


@pytest.mark.parametrize("path", ["", "/src"])
async def test_directory_listing(client, upstream, path):
    authenticate(upstream)
    connected(upstream)
    token = mint(upstream)
    entries = [{"path": "src/main.py", "type": "file", "size": 12, "sha": HEAD}]
    read = upstream.get(
        f"{GH}/repos/{REPO}/contents/{path.lstrip('/')}", params={"ref": BRANCH}
    ).respond(200, json=[{**entries[0], "url": "unused"}])
    response = await client.get(f"/v1/projects/{APP_ID}/files{path}")
    assert response.status_code == 200
    assert response.json() == entries
    assert read.called
    assert_scoped(token)


@pytest.mark.parametrize("raw,encoding", [("héllo\n".encode(), "utf-8"), (b"\xff\x00", "base64")])
async def test_file_read_ref_and_binary_encoding(client, upstream, raw, encoding):
    authenticate(upstream)
    connected(upstream)
    mint(upstream)
    encoded = base64.b64encode(raw).decode()
    upstream.get(
        f"{GH}/repos/{REPO}/contents/src/a%20b.txt", params={"ref": "other/branch"}
    ).respond(
        200,
        json={"path": "src/a b.txt", "sha": HEAD, "encoding": "base64", "content": encoded + "\n"},
    )
    response = await client.get(f"/v1/projects/{APP_ID}/files/src/a%20b.txt?ref=other/branch")
    assert response.status_code == 200
    assert response.json() == {
        "path": "src/a b.txt",
        "sha": HEAD,
        "encoding": encoding,
        "content": raw.decode() if encoding == "utf-8" else encoded,
    }


async def test_stale_base_sha_returns_current_head_without_writes(client, upstream):
    authenticate(upstream)
    connected(upstream)
    mint(upstream)
    upstream.get(f"{GH}/repos/{REPO}/git/ref/heads/feature%2Fwork").respond(
        200, json={"object": {"sha": NEW_HEAD}}
    )
    response = await client.put(f"/v1/projects/{APP_ID}/files", json=BATCH)
    assert response.status_code == 409
    assert response.json()["detail"]["current_sha"] == NEW_HEAD
    assert NEW_HEAD in response.json()["detail"]["hint"]
    assert not any("/git/blobs" in str(call.request.url) for call in upstream.calls)


def mock_commit(upstream):
    authenticate(upstream)
    connected(upstream)
    token = mint(upstream)
    head = upstream.get(f"{GH}/repos/{REPO}/git/ref/heads/feature%2Fwork").respond(
        200, json={"object": {"sha": HEAD}}
    )
    upstream.get(f"{GH}/repos/{REPO}/git/commits/{HEAD}").respond(
        200, json={"tree": {"sha": "base-tree"}}
    )
    blob = upstream.post(f"{GH}/repos/{REPO}/git/blobs").respond(201, json={"sha": "blob-sha"})
    tree = upstream.post(f"{GH}/repos/{REPO}/git/trees").respond(201, json={"sha": "new-tree"})
    commit = upstream.post(f"{GH}/repos/{REPO}/git/commits").respond(201, json={"sha": NEW_HEAD})
    update = upstream.patch(f"{GH}/repos/{REPO}/git/refs/heads/feature%2Fwork").respond(
        200, json={"object": {"sha": NEW_HEAD}}
    )
    return token, head, blob, tree, commit, update


async def test_batch_commit_includes_delete_and_empty_file(client, upstream):
    token, _, blob, tree, commit, update = mock_commit(upstream)
    files = BATCH["files"] + [{"path": "old.py", "content": None}, {"path": "empty", "content": ""}]
    response = await client.put(f"/v1/projects/{APP_ID}/files", json={**BATCH, "files": files})
    assert response.status_code == 200
    assert response.json() == {"commit_sha": NEW_HEAD, "previous_sha": HEAD}
    assert_scoped(token)
    assert len(blob.calls) == 2
    assert json.loads(blob.calls[0].request.content) == {
        "content": "print('hello')",
        "encoding": "utf-8",
    }
    assert json.loads(blob.calls[1].request.content)["content"] == ""
    assert json.loads(tree.calls.last.request.content) == {
        "base_tree": "base-tree",
        "tree": [
            {"path": "main.py", "mode": "100644", "type": "blob", "sha": "blob-sha"},
            {"path": "old.py", "mode": "100644", "type": "blob", "sha": None},
            {"path": "empty", "mode": "100644", "type": "blob", "sha": "blob-sha"},
        ],
    }
    assert json.loads(commit.calls.last.request.content) == {
        "message": "Update app",
        "tree": "new-tree",
        "parents": [HEAD],
    }
    assert json.loads(update.calls.last.request.content) == {"sha": NEW_HEAD, "force": False}


@pytest.mark.parametrize("status", [409, 422])
async def test_concurrent_push_conflict(client, upstream, status):
    _, head, _, _, _, update = mock_commit(upstream)
    head.side_effect = [
        httpx.Response(200, json={"object": {"sha": HEAD}}),
        httpx.Response(200, json={"object": {"sha": "c" * 40}}),
    ]
    update.respond(status, json={"message": "Update is not a fast forward"})
    response = await client.put(f"/v1/projects/{APP_ID}/files", json=BATCH)
    assert response.status_code == 409
    assert response.json()["detail"]["current_sha"] == "c" * 40
    assert update.call_count == 1


async def test_git_tokens_are_fresh_per_caller_and_headers_forwarded(client, upstream):
    authenticate(upstream)
    connected(upstream)
    token = mint(upstream)
    token.side_effect = [
        httpx.Response(201, json=TOKEN),
        httpx.Response(
            201,
            json={
                **TOKEN,
                "token": "second-token",
            },
        ),
    ]
    first = await client.post(f"/v1/projects/{APP_ID}/git-token")
    client.headers["Authorization"] = "Bearer floo_other"
    client.headers.pop("X-Floo-Org-Id")
    second = await client.post(f"/v1/projects/{APP_ID}/git-token")
    assert first.status_code == second.status_code == 200
    assert first.json() == {**TOKEN, "clone_url": f"https://github.com/{REPO}.git"}
    assert second.json()["token"] == "second-token"
    assert first.headers["Cache-Control"] == second.headers["Cache-Control"] == "no-store"
    assert token.call_count == 2
    assert_scoped(token)
    floo_calls = [call for call in upstream.calls if call.request.url.host == "floo.test"]
    assert len(floo_calls) == 6
    for call in floo_calls[3:]:
        assert call.request.headers["Authorization"] == "Bearer floo_other"
        assert "X-Floo-Org-Id" not in call.request.headers


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "files", None),
        ("PUT", "files", BATCH),
        ("POST", "git-token", None),
    ],
)
@pytest.mark.parametrize("repo", ["foreign/repo", "managed-evil/repo", "managed/../oops", None])
async def test_unmanaged_repo_never_mints_token(client, upstream, method, suffix, body, repo):
    authenticate(upstream)
    connected(upstream, repo=repo)
    response = await client.request(method, f"/v1/projects/{APP_ID}/{suffix}", json=body)
    assert response.status_code == 404
    assert all(call.request.url.host == "floo.test" for call in upstream.calls)


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "files", None),
        ("PUT", "files", BATCH),
        ("POST", "git-token", None),
    ],
)
async def test_app_access_denied_before_github(client, upstream, method, suffix, body):
    authenticate(upstream)
    envelope = {"detail": {"code": "FORBIDDEN", "message": "No app access.", "hint": "Select org."}}
    upstream.get(f"{FLOO}/v1/apps/{APP_ID}").respond(403, json=envelope)
    response = await client.request(method, f"/v1/projects/{APP_ID}/{suffix}", json=body)
    assert response.status_code == 403
    assert response.json() == envelope
    assert len(upstream.calls) == 2


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/v1/projects", {"name": "demo"}),
        ("PUT", f"/v1/projects/{APP_ID}/files", BATCH),
        ("POST", f"/v1/projects/{APP_ID}/git-token", None),
    ],
)
async def test_read_scope_cannot_mutate_or_receive_push_token(client, upstream, method, path, body):
    authenticate(upstream, scope="read")
    response = await client.request(method, path, json=body)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INSUFFICIENT_KEY_SCOPE"
    assert len(upstream.calls) == 1


@pytest.mark.parametrize(
    "files",
    [
        [],
        [{"path": "../secret", "content": "secret-value"}],
        [{"path": "/absolute", "content": "secret-value"}],
        [{"path": "x", "content": "a"}, {"path": "x", "content": None}],
    ],
)
async def test_invalid_batch_is_rejected(client, upstream, files):
    authenticate(upstream)
    response = await client.put(f"/v1/projects/{APP_ID}/files", json={**BATCH, "files": files})
    assert response.status_code == 422
    assert "secret-value" not in response.text
    assert all(call.request.url.host == "floo.test" for call in upstream.calls)


async def test_null_scope_allows_reads_but_denies_writes(client, upstream):
    authenticate(upstream, scope=None)
    upstream.get(f"{FLOO}/v1/apps", params={"page": 1, "per_page": 100}).respond(
        200, json={"apps": [], "total": 0, "page": 1, "per_page": 100}
    )
    response = await client.get("/v1/projects")
    assert response.status_code == 200
    assert response.json() == []
    response = await client.put(f"/v1/projects/{APP_ID}/files", json=BATCH)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INSUFFICIENT_KEY_SCOPE"
    assert len(upstream.calls) == 3


async def test_floo_network_error(client, upstream):
    upstream.get(f"{FLOO}/v1/auth/whoami").mock(side_effect=httpx.ConnectError("offline"))
    response = await client.get("/v1/projects")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "FLOO_UNAVAILABLE"


async def test_github_error(client, upstream):
    authenticate(upstream)
    connected(upstream)
    upstream.post(TOKEN_URL).respond(403, json={"message": "Installation suspended"})
    response = await client.post(f"/v1/projects/{APP_ID}/git-token")
    assert response.status_code == 403
    assert response.json()["detail"]["message"] == "Installation suspended"
