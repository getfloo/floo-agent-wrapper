# floo managed app

A Next.js App Router app on floo: hosted, invite-only login, managed Postgres
with Drizzle, a signed-in UI at `/`, and a key-authenticated JSON API at
`/api` that any program or agent can call.

`AGENTS.md` is the working guide: layout, identity rules, local runs, schema
changes, adding an API endpoint, declaring services, and deployment commands.

## Local development

```sh
npm install
floo dev
```

`floo dev` prints the local URL and supplies identity and database
credentials. The deployed service must stay behind floo's gateway in accounts
mode.

## Ship

```sh
npm run build
npm test
git add .
git commit -m "Update app"
git push
floo deploys watch
```

Each new revision applies the committed migrations when it starts, before it
serves. Builds and tests need no database. Tailwind v4 configuration lives in
`app/globals.css` and `postcss.config.mjs`.
