import "server-only";
import { desc, eq } from "drizzle-orm";
import { getDb } from "@/db";
import { notes } from "@/db/schema";

export const MAX_NOTE_LENGTH = 5000;

/** Thrown for input the caller can fix; the API answers it with 400, the form shows it. */
export class InvalidNote extends Error {}

// One validation for the form action and the JSON route, so they cannot drift.
export function parseNoteBody(value: unknown): string {
  if (typeof value !== "string" || !value.trim() || value.length > MAX_NOTE_LENGTH) {
    throw new InvalidNote(`Write a note between 1 and ${MAX_NOTE_LENGTH.toLocaleString("en-US")} characters.`);
  }
  return value.trim();
}

export type Note = typeof notes.$inferSelect;

export async function listNotes(ownerId: string): Promise<Note[]> {
  return getDb().select().from(notes).where(eq(notes.ownerId, ownerId)).orderBy(desc(notes.createdAt));
}

export async function createNote(ownerId: string, body: string): Promise<Note> {
  const [note] = await getDb().insert(notes).values({ ownerId, body }).returning();
  return note;
}
