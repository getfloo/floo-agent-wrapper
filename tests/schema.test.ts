import { readFileSync } from "node:fs";
import { readMigrationFiles } from "drizzle-orm/migrator";
import { describe, expect, it } from "vitest";

describe("committed migration", () => {
  const migrations = readMigrationFiles({ migrationsFolder: "./drizzle" });
  const sql = migrations.flatMap((migration) => migration.sql).join("\n");
  const tables = new Map(Array.from(
    sql.matchAll(/CREATE TABLE "(\w+)"\s*\(([\s\S]*?)\n\);/g),
    ([, name, columns]) => [name, columns],
  ));

  it("creates users with the gateway ID and profile fields", () => {
    expect(tables.get("users")).toMatch(/"id" text PRIMARY KEY NOT NULL/);
    for (const column of ["email", "name", "role", "created_at", "updated_at"]) {
      expect(tables.get("users")).toContain(`"${column}"`);
    }
  });

  it("creates notes with a user foreign key and an ownership index", () => {
    expect(tables.get("notes")).toMatch(/"id" uuid PRIMARY KEY DEFAULT gen_random_uuid\(\) NOT NULL/);
    expect(tables.get("notes")).toContain('"user_id" text NOT NULL');
    expect(tables.get("notes")).toContain('"body" text NOT NULL');
    expect(tables.get("notes")).toContain('"created_at"');
    expect(sql).toMatch(/FOREIGN KEY \("user_id"\) REFERENCES "users"\("id"\)/);
    expect(sql).toContain('ON "notes" USING btree ("user_id","created_at")');
  });

  it("keeps SQL portable across managed tenant schemas", () => {
    expect(sql).not.toMatch(/"public"\.|CREATE SCHEMA|SET search_path/i);
    const journal = JSON.parse(readFileSync("drizzle/meta/_journal.json", "utf8"));
    expect(journal.entries).toHaveLength(migrations.length);
    expect(migrations.length).toBeGreaterThan(0);
  });
});
