FROM node:22-bookworm-slim AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS builder
COPY . .
RUN npm run build

FROM dependencies AS production-dependencies
RUN npm prune --omit=dev

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
# Migrations run in this image at container start, so it keeps tsx, the ORM and the driver.
COPY --from=production-dependencies --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/scripts/migrate.ts ./scripts/migrate.ts
COPY --from=builder --chown=node:node /app/drizzle ./drizzle
USER node
EXPOSE 3000
# The first instance of a new revision migrates before it serves. migrate.ts holds an
# advisory lock, so concurrent instances wait for it and then find nothing to apply.
# A failed migration exits non-zero: the revision never becomes ready and the previous
# one keeps serving. This replaces a separate migration job, which waited minutes
# for a container on every deploy.
CMD ["sh", "-c", "node_modules/.bin/tsx scripts/migrate.ts && exec node server.js"]
