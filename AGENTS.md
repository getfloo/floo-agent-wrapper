# floo managed app

A live Next.js App Router app behind floo's gateway, with managed Postgres, a
signed-in UI at `/` and a key-authenticated JSON API at `/api`.
Keep one web service, TypeScript, Drizzle with postgres, and Tailwind CSS v4.

## Where to work
- Pages and layouts: `app/`; global styles and Tailwind theme: `app/globals.css`.
- Server actions: `app/actions.ts` (`"use server"`).
- JSON API: `app/api/<name>/route.ts`, its contract in `app/api/<name>/openapi.ts`;
  the example is `app/api/notes/`. The spec is served at `/api/openapi.json`.
- Feature logic shared by pages, actions and the API: `lib/notes.ts`. Validate once there.
- Tables: `db/schema.ts`; connection: `db/index.ts`; user directory: `db/users.ts`.
- SQL and snapshots: `drizzle/`; migration runner: `scripts/migrate.ts`.
- Who is calling: `lib/identity.ts`; tests: `tests/*.test.ts`.

## Callers and identity
Never add auth, sessions, tokens, login pages, sign-out, or local identity stubs.
The gateway is the only ingress (`access_mode = "accounts"`) and it asserts who
is calling in `X-Floo-*` headers; it strips any the client sent.
- Pages and actions serve signed-in people. Call `getIdentity()`; it returns
  `{ kind: "user", id, email, name, role }` and throws if the request did not
  come through the gateway. Roles pass through unchanged.
- `/api` serves programs holding an app API key. Call `callerFrom(request.headers)`;
  it returns either that user or `{ kind: "api_key", id, name, keyId, scopes }`,
  where `id` is the key's consumer, stable across key rotation.
- Use the returned `id` for ownership filters and inserts, never a submitted id.
- Use `getDb()`; `DATABASE_URL` is the only credential this app reads. Never
  write connection strings or read `PG*`, keys, or other credentials.

## Run locally (Node.js 22.12+, 24+, or 26+)
```sh
npm install
floo dev
# In another terminal:
npm test
```
Open the URL printed by `floo dev`; it supplies a signed-in identity and the
database. `npm test` runs route type generation, typecheck, lint, and Vitest
without a database. Key-authenticated calls are tested against the deployed
app (below), not locally.

## Add a table and ship
```sh
# edit db/schema.ts
npm run db:generate
git add db/schema.ts drizzle/
npm run build && npm test
git add . && git commit -m "Add application feature"
git push
floo deploys watch
```
Generate through this script so SQL references stay schema independent.
Commit the generated SQL, journal, and snapshots; never edit applied migrations.
The web container runs `npm run db:migrate` when it starts, before it serves.
A failed migration keeps the previous revision live.

## Add an API endpoint
1. Put the handler at `app/api/<name>/route.ts`, export `GET`/`POST`, and read the
   caller with `callerFrom(request.headers)`. Everything under `/api` is already
   declared in `floo.app.toml` (`[[routes]]`, `access = "api_key"`, `scope = "api"`);
   add a new `[[routes]]` entry only for a path outside `/api`.
2. Validate input with a zod schema in `lib/<feature>.ts` and share it and the
   queries with the UI.
3. Describe the endpoint in `app/api/<name>/openapi.ts` with that same schema and
   add its `operations` to the list in `app/api/openapi.json/route.ts`. `npm test`
   fails if a handler is undocumented or a response does not match its schema.
4. Push, then mint a key and call it:
```sh
floo apps consumers create my-agent
floo apps keys create my-agent-key --consumer my-agent --scope api   # prints the key once
curl -H "Authorization: Bearer $KEY" https://<app>-dev.on.getfloo.com/api/notes
curl -H "Authorization: Bearer $KEY" https://<app>-dev.on.getfloo.com/api/openapi.json
```
Hand another agent the app URL and a key: `/api/openapi.json` tells it the rest.
Wrong or missing keys get the gateway's 401 before reaching the app. Scopes are
exact labels: a key must hold the route's `scope` to pass.

## Services you can declare (in floo.app.toml, changed through git)
- Postgres: `[managed.default] type = "postgres"` injects `DATABASE_URL` (present).
  A second one, `[managed.<name>]`, injects `DATABASE_URL_<NAME>`.
- Redis: `[managed.cache] type = "redis"` injects `REDIS_URL_CACHE`; as
  `[managed.default]` it would be `REDIS_URL`. Cache only, no durability.
- File storage: `[managed.files] type = "storage"` injects `STORAGE_BUCKET_FILES`
  and `STORAGE_URL_FILES`.
- Cron: `[cron.<name>]` with `schedule` (UTC; there is no timezone field),
  `command`, `service = "web"`, `timeout`. The command runs in this image, so
  package its script in `Dockerfile` and keep `tsx` to run TypeScript.
- Environment variables: list required names under
  `[services.web.env] required = [...]`, then `floo env set NAME=value`, or
  `floo env set NAME --stdin --secret` for a secret. Read back with
  `floo env get NAME --json`; `floo env list` masks values. floo owns `DATABASE_URL`.

## When a deploy fails
`floo deploys watch` names the failed step. `floo deploys logs` shows the build
and startup output, including a failed migration. `floo logs query` reads the
running app's logs; `floo logs tail` never exits.
