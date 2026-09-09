# floo managed app

This is a live Next.js App Router app with gateway identity and managed Postgres.
Keep one web service, TypeScript, Drizzle with postgres, and Tailwind CSS v4.

## Where to work
- Pages and layouts: `app/`; global styles and Tailwind theme: `app/globals.css`.
- Server actions: `app/actions.ts` (`"use server"`); validate submitted data here.
- Tables: `db/schema.ts`; connection: `db/index.ts`; user upsert: `db/users.ts`.
- SQL and snapshots: `drizzle/`; migration runner: `scripts/migrate.ts`.
- Identity: `lib/identity.ts`; tests: `tests/*.test.ts`.

## Identity and database rules
Never add auth, sessions, tokens, login pages, sign-out, or local identity stubs.
Call `getIdentity()` in every page/action that uses user data.
It reads X-Floo-User-Email, X-Floo-User-Id, X-Floo-User-Name, X-Floo-User-Role.
Missing or blank headers throw; roles are passed through without inventing defaults.
Headers are trustworthy ONLY because the gateway is the sole service ingress in
accounts mode. Keep `access_mode = "accounts"`; never expose a direct service URL.
Use the returned ID for ownership filters and inserts, never a submitted user ID.
Use `getDb()`; DATABASE_URL is the only credential this template reads.
Never write connection strings or read PG*, auth keys, or other credentials.
Keep `[managed.default]`: named Postgres resources get suffixed URL variables.
Use unqualified tables; floo's database role sets the app/environment search_path.

## Run locally (Node.js 22.12+, 24+, or 26+)
```sh
npm install
floo dev
# In another terminal:
npm test
```
Open the URL printed by `floo dev`; it supplies identity and database credentials.
`scripts/test` runs route type generation, typecheck, lint, and Vitest without a DB.

## Add a table and ship
```sh
vi db/schema.ts
npm run db:generate
git add db/schema.ts drizzle/
npm run build
npm test
git add .
git commit -m "Add application feature"
git push
floo deploys watch
```
Generate through this script so SQL references stay tenant-schema independent.
Commit the generated SQL, journal, and snapshots; never edit applied migrations.
Deploy runs `npm run db:migrate` before serving the new revision.

## Add a cron or environment variable
Edit `floo.app.toml`: declare jobs under `[cron.<name>]`; put required variable
names in `[services.web.env] required = ["VARIABLE_NAME"]`. Keep values off git.
Package a cron's script in `Dockerfile` so it exists in the deployed image.
```sh
vi floo.app.toml
vi Dockerfile
floo env set --help
floo env set VARIABLE_NAME=value
git add floo.app.toml Dockerfile
git commit -m "Configure app jobs and environment"
git push
floo deploys watch
```
Use `floo env set` only for intentionally added app configuration; floo owns
DATABASE_URL. Do not add credential fallbacks to the template.
