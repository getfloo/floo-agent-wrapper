# floo-agent-wrapper

A floo project that lives without a GitHub account.

## Thesis

Agents get an order of magnitude more useful when they can build durable tools
for themselves and hand the human an app with a URL, a login, and a database.
floo already does the hard parts: build from Git, managed Postgres, secrets,
hosted login with invite-only membership, cron, logs, and a database query
endpoint. The one thing standing between a personal agent and "build me an
invoice tracker" is that floo deploys only from GitHub, and the agent's user
has no GitHub account.

The wrapper closes that gap and nothing else.

## What exists today (verified 2026-09-09)

- Every platform action is an HTTP endpoint under `/v1`: apps, deploys and log
  streams, env, managed services, `db/schema`, `db/query`, cron run, invites,
  memberships. The CLI client enumerates them.
- GitHub is the only source of truth for code. There is no upload path; the
  API fetches a repo tarball at deploy time. This is a hard invariant and the
  wrapper keeps it.
- A GitHub App installation is required before any deploy. Installation
  bindings are keyed `(org_id, installation_id)`, and the model comment says
  two floo orgs may legitimately share one installation. A binding row is only
  written after a browser handshake, because that handshake is the
  authorization decision.
- Accounts mode gives an app a hosted login page and identity headers.
  Admission is invitation-only via `AppMembership`.
- Managed Postgres is one manifest block; credentials are injected at deploy;
  `migrate_command` runs before traffic shifts.
- Platform API keys can be minted from the dashboard. The CLI installs with
  `curl -fsSL https://getfloo.com/install.sh | bash` and bundles a `floo`
  skill.
- No MCP server, no templates, no repo creation anywhere in floo.
- Prior art: getfloo/floo#696 covers the other direction, agent-facing
  interfaces for deployed apps. This plan is the agent-facing interface to the
  platform. Build this first; #696 is milestone 3.

## Who calls it

- **Muse (consumer).** No third-party connector slot, but a Linux VM with git,
  a shell, crons, and Meta's own line: "Muse can also write its own custom
  connectors for other services you care about if they have their own APIs or
  CLIs," using credentials the user provides. Real credentials never enter the
  VM; a surrogate token is swapped at the egress proxy. So the Muse path is
  the floo CLI plus a short-lived git credential. The only long-lived secret
  is the floo key, which fits Meta's model exactly.
- **Muse Code, Claude Code, Cursor.** Same as Muse: CLI plus git. Optionally
  the same tools over stdio MCP.
- **claude.ai, ChatGPT.** No VM. They take a pasted remote MCP URL with OAuth.
  They need file read and write over HTTP because they cannot run git.
- **Instinct.** No documented third-party path. Partnership pitch only.

## What the wrapper owns

1. **A floo-owned GitHub org.** Every managed project is a private repo
   there, named by floo org and app. The user never sees it.
2. **Create project.** Repo from the template, floo app in the user's org,
   connected to the shared installation, Postgres and accounts mode preset.
   Returns `app_url` and `clone_url`.
3. **Git access without GitHub.** Short-lived installation tokens, issued only
   to a valid floo key with rights on that app. Two transports, one
   authorization:
   - VM agents: a `floo git-credential` helper.
   - No-VM agents: a batch file write that commits through the GitHub API and
     requires the caller's `base_sha`, so two agents cannot silently overwrite
     each other.
4. **Read project.** File listing and contents, so a fresh conversation can
   orient before editing.
5. **Export.** Transfer the repo to the user's own GitHub. Later, but it is
   what makes "no GitHub" a feature rather than lock-in.

Surface, v1:

```
POST   /projects                      create from template -> app_url, clone_url
GET    /projects                      list mine
GET    /projects/{app}/files[/path]   read
PUT    /projects/{app}/files          commit a batch, requires base_sha
POST   /projects/{app}/git-token      short-lived push credential
POST   /projects/{app}/export         transfer to the user's GitHub (later)
```

The wrapper is stateless. Durable truth lives in floo and GitHub.

## What the wrapper does not own

Deploys, deploy status, logs, env, databases, cron, invites, auth. Those are
existing floo endpoints. Agents call them directly, or the MCP layer proxies
them one-to-one with no added logic.

## The one platform change

An opt-in that binds a user org to the platform-managed installation without
the browser handshake. The data model already permits the shared binding; the
change is a second, deliberate authorization path for orgs that choose managed
projects. Verify that the deploy tarball pull works off that installation for
a user org's app before building anything else.

## Template

One stack, chosen for what agents write correctly on the first try. Accounts
mode on, Postgres declared, `migrate_command` wired, identity headers read on
the server, a working page behind login. Agents edit from a running baseline
instead of scaffolding.

## Recipe

A public page, `getfloo.com/agents/build-an-app.md`, linked from `llms.txt`
and from the CLI's bundled skill, written the way Meta writes connector
SKILLs. For a VM agent:

```
curl -fsSL https://getfloo.com/install.sh | bash
floo auth login --api-key <pasted from dashboard>
floo apps create invoice-tracker --template saas
cd invoice-tracker && <edit> && git push
floo deploy status --wait
floo apps invite client@example.com
```

Everything except the create line works today.

## Milestones

1. **Muse path.** Shared installation, floo-owned org, template, credential
   helper, recipe page, dashboard "connect an agent" button. Demo: one pasted
   key, Muse builds a client portal, an invited client signs in.
2. **No-VM path.** Remote MCP with OAuth over the same endpoints plus file
   read and write. Demo in claude.ai: a fresh chat lists projects, queries
   yesterday's data, adds a feature, redeploys.
3. **Use what it built.** App-declared actions with scoped agent access.
   That is getfloo/floo#696. Defer until milestone 2 proves demand; the db
   query endpoint and cron already give agents a "use" loop without app
   changes.

Then the Meta pitch: our SKILL, our API, and a recording of milestone 1. That
is the same shape as Meta's built-in connectors, so asking to be one is a
small ask.

## Verify before building

- Muse's egress proxy evaluates every request. Confirm a new host such as the
  floo API needs no allowlisting. A five-minute test with a Muse account
  settles it.
- Deploy tarball pull off the shared installation for a user org's app.

## What this deliberately does not build

- Public self-signup. Invite-only stays.
- A marketplace, hosted agents, or a wrapper-owned database.
- A second deploy path. Code still deploys from Git.
- App-side agent interfaces (#696) before milestone 2 proves demand.

Replaces: nothing; there is no agent surface today.

Delete when: the floo API grows managed repos and a native MCP endpoint, at
which point this repo's endpoints move in and the repo is archived.
