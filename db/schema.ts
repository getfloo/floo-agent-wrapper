import { index, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";

/** People who have signed in, synced from the gateway on every page load. */
export const users = pgTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull(),
  name: text("name").notNull(),
  role: text("role").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// owner_id is whatever id the gateway asserted: a user's id from the page, or an
// API consumer's id from /api. It is not a foreign key to users because a key
// caller is not a user.
export const notes = pgTable("notes", {
  id: uuid("id").defaultRandom().primaryKey(),
  ownerId: text("owner_id").notNull(),
  body: text("body").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (table) => [index("notes_owner_id_created_at_idx").on(table.ownerId, table.createdAt)]);
