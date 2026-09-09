import { readMigrationFiles } from "drizzle-orm/migrator";
import postgres from "postgres";

const url = process.env.DATABASE_URL;
if (!url) {
  throw new Error("Missing DATABASE_URL. floo injects managed Postgres credentials at migration time.");
}

const client = postgres(url, { max: 1 });
try {
  // Keep the migration journal in the tenant schema, never a shared drizzle schema.
  const [row] = await client<{ schema: string }[]>`select current_schema() as schema`;
  if (!row?.schema || row.schema === "public") {
    throw new Error("Expected a floo-managed tenant schema in the database search_path.");
  }
  const migrations = readMigrationFiles({ migrationsFolder: "./drizzle" });
  // Drizzle's default migrator issues CREATE SCHEMA, which tenant roles cannot do.
  // Use its migration files and journal format within the existing search_path.
  await client.begin(async (transaction) => {
    await transaction`select pg_advisory_xact_lock(hashtext(current_schema()), hashtext('floo-drizzle-migrations'))`;
    await transaction`CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
      id SERIAL PRIMARY KEY, hash text NOT NULL, created_at bigint NOT NULL
    )`;
    const applied = await transaction<{ hash: string; created_at: string }[]>`
      SELECT hash, created_at FROM "__drizzle_migrations" ORDER BY created_at
    `;
    for (const migration of migrations) {
      const previous = applied.find((entry) => Number(entry.created_at) === migration.folderMillis);
      if (previous) {
        if (previous.hash !== migration.hash) {
          throw new Error("An applied migration changed. Restore it and generate a new migration.");
        }
        continue;
      }
      for (const statement of migration.sql) {
        await transaction.unsafe(statement);
      }
      await transaction`INSERT INTO "__drizzle_migrations" (hash, created_at)
        VALUES (${migration.hash}, ${migration.folderMillis})`;
    }
  });
} finally {
  await client.end();
}
