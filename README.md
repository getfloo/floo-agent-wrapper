# floo agent wrapper

Stateless FastAPI API for creating floo apps backed by private, managed GitHub
repos. GitHub remains the code source of truth; deployments use floo unchanged.

Set these environment variables (Python 3.12+ and `uv` required):

| Variable | Value |
| --- | --- |
| `FLOO_API_URL` | Optional; defaults to `https://api.getfloo.com` |
| `GITHUB_APP_ID` | GitHub App numeric ID |
| `GITHUB_APP_PRIVATE_KEY` | Unencrypted RSA PEM; literal `\n` escapes accepted |
| `GITHUB_INSTALLATION_ID` | App installation ID in the managed org |
| `GITHUB_MANAGED_ORG` | Managed org, e.g. `floo-apps` |
| `GITHUB_TEMPLATE_REPO` | Accessible template, `owner/repo` |

```sh
uv sync
uv run uvicorn app.main:app --reload --port 8000
scripts/test
```

Send `Authorization: Bearer floo_...` to every `/v1` route, plus optional
`X-Floo-Org-Id` to select an org; both are forwarded unchanged to floo. Without
the org header, floo selects the most recently joined org. Open `/docs` for
create/list projects, read files (`?ref=`), batch commits, and git tokens.
V1 batch commits accept UTF-8 text only and always write mode 100644, so binary files and executable bits go through `git push` with a git token instead.
Writes and push tokens require effective `write` or `admin` scope. `/healthz`
needs no authentication. Missing settings or an invalid PEM fail at startup.

The GitHub installation must cover new repos and allow administration/contents
write and metadata read. Repo creation uses an internal installation-wide
credential; every file request and returned git token gets a fresh credential
scoped to one repo. Credentials and project facts are never persisted or cached.
The floo org must already be allowed to connect the managed installation;
this service does not add that platform binding. A failed connection preserves
the app/repo and returns floo's error with IDs and retry instructions in its hint.

Tests mock all floo/GitHub traffic. Deploy with the included Dockerfile and
`floo.app.toml` (web service, port 8000); inject credentials as floo secrets.
