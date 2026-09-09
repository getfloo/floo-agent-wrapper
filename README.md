# floo app template

A working Next.js app with gateway-provided identity, managed Postgres, and
personal notes. Built with TypeScript, Drizzle, and Tailwind CSS.

**Start with [AGENTS.md](AGENTS.md)** for the file map, identity rules, schema
changes, and deployment commands. [PLAN.md](PLAN.md) contains the project design.

With Node.js 22.12+, 24+, or 26+ and the floo CLI configured for your project:

```sh
npm install
floo dev
```

Open the URL floo prints. It supplies the signed-in user's headers and
`DATABASE_URL`; there are no auth keys or connection strings to configure.
The deployed service must stay behind floo's gateway in accounts mode.

```sh
npm run build
npm test
git add .
git commit -m "Update app"
git push
floo deploys watch
```

Deploy applies the committed migrations automatically. Builds and tests need no
database. Tailwind v4 configuration lives in `app/globals.css` and
`postcss.config.mjs`.
