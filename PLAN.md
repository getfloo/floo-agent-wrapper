# Managed projects: floo for agents

An agent turns "build me an app" into a deployed floo app with login and a
database, without the user owning a GitHub account.

## Decisions (2026-09-09)

- Lives in the floo monorepo as one isolated package, `api/app/projects/`,
  plus CLI commands in floo-cli. This repo becomes the app template.
- Supported agent tiers: shell plus git (Muse, Muse Code, Claude Code,
  Cursor) and HTTP only (claude.ai, ChatGPT). Browser-only agents are not a
  design input.
- Two GitHub Apps. The existing floo App stays read-and-deploy everywhere.
  A second "floo managed" App with Administration holds only the managed
  orgs, so no customer installation ever grants floo admin.
- Managed orgs are a list, not a singleton. GitHub's per-installation REST
  rate limit is the scale ceiling, so orgs shard. v1 config holds one.
- Repo name is `floo-<org_id hex32>-<app_id hex32>`. Only floo has admin on
  the managed orgs, so a floo-minted name is the ownership proof:
  connect-time authorization parses the org and app ids from the name. No
  topic, no table.
- Create deploys the template immediately. The agent gets a live URL with
  working login before writing code.
- Git is the primary transport. The CLI ships a credential helper that fetches
  a one-hour repo-scoped token from floo. HTTP file read and batch commit
  exist for agents without git.
- Template stack: Next.js, TypeScript, Drizzle, Postgres, Tailwind. One web
  service, accounts mode, one example table, `AGENTS.md` for orientation.
- Everything the agent installs lives in its workspace. Nothing system-wide.

## What exists in floo today (verified)

- Every platform action is under `/v1`: apps, deploys and log streams, env,
  managed Postgres, `db/query`, cron run, invites, memberships.
- GitHub is the only source of truth for code; deploys pull a repo tarball
  using the installation resolved from the repo owner. Deploys need no change.
- Installation bindings are `(org_id, installation_id)`; two orgs may share
  one installation. A binding is written only after a browser handshake. The
  invariant "installation ids are not reusable across orgs" gains one
  deliberate exception for managed repos.
- Accounts mode: hosted login, identity headers, invite-only membership.
- `floo dev` runs services locally with managed-service credentials and a
  proxy that injects identity headers. `floo deploys watch`, `floo logs`,
  `floo db query`, `floo env set`, `floo apps invite` exist.
- Platform API keys are minted in the dashboard. CLI installs via
  `curl -fsSL https://getfloo.com/install.sh | bash` and honors
  `FLOO_INSTALL_DIR`.

## Agent experience

Once: fetch `getfloo.com/agents.md`, ask the user for a key from the
dashboard's "Connect an agent" button, install the CLI into the workspace,
`floo auth login --api-key`.

Day 1:

```
floo projects create client-portal      # live URL, login, postgres, repo; first deploy done
floo projects clone client-portal       # git clone with the credential helper set locally
# read AGENTS.md, add tables/pages, never touch auth
floo dev --as pat@studio.com && npm test
git commit -am "Invoices per customer" && git push
floo deploys watch                      # step-named errors with the next command
floo apps invite alice@customer.com --role viewer
```

Later: `floo db query` and cron to act on the app's data without code
changes; `floo env set` for secrets; `floo projects list` to come back cold;
`floo projects export` to hand the repo to a developer (later milestone).

HTTP agents run the same loop: `POST/GET /v1/projects`, file read, batch
commit with `base_sha`, and the existing deploy, log, env, db, and invite
endpoints. An MCP adapter over these is a thin later layer.

Rules that make it simple: one stack, green on create, every error carries
the next command, nothing system-wide, the agent never writes auth.

## Work

1. **API** (`api/app/projects/`): `POST /v1/projects` (create app, generate
   repo, connect, first deploy), `GET /v1/projects`, `POST
   /v1/projects/{app}/git-token`, name-derived authorization in connect,
   managed-App settings, knowledge article.
2. **CLI**: `floo projects create|list|clone`, `floo projects git-credential`
   (git credential helper protocol), API client methods, docs.
3. **Template**: this repo, renamed `floo-app-template`.
4. **Recipe page** `getfloo.com/agents.md` and dashboard "Connect an agent".
5. **HTTP files**: `GET /v1/projects/{app}/files[/path]`,
   `PUT /v1/projects/{app}/files` (batch, `base_sha`, 409 on stale).
6. **Export**, then MCP adapter, then app-declared actions (getfloo/floo#696).

Tracking: getfloo/floo#2534.

## Verify

- Muse's egress proxy reaches `api.getfloo.com` without allowlisting. One
  `curl` to whoami with a key.
- The floo App's tarball pull works from a managed org (expected: yes, the
  installation is resolved from the repo owner).

## Deliberately not building

Public self-signup, a marketplace, hosted agents, a second deploy path, a
wrapper service, wrapper-owned state, browser-only agent support.
