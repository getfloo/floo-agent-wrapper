import "server-only";
import { desc, eq } from "drizzle-orm";
import { z } from "zod";
import { getDb } from "@/db";
import { notes } from "@/db/schema";

export const MAX_NOTE_LENGTH = 5000;
const INVALID_BODY = `Write a note between 1 and ${MAX_NOTE_LENGTH.toLocaleString("en-US")} characters.`;

// One schema validates the form action and POST /api/notes, and the OpenAPI
// document is generated from it, so the three cannot drift.
export const NoteInput = z.object({
  body: z.string({ error: INVALID_BODY })
    .trim()
    .min(1, { error: INVALID_BODY })
    .max(MAX_NOTE_LENGTH, { error: INVALID_BODY })
    .meta({ description: "The note text. Leading and trailing whitespace is removed." }),
});

/** Thrown for input the caller can fix; the API answers it with 400, the form shows it. */
export class InvalidNote extends Error {}

export function parseNoteInput(value: unknown): z.infer<typeof NoteInput> {
  const parsed = NoteInput.safeParse(value);
  if (!parsed.success) {
    throw new InvalidNote(parsed.error.issues[0].message);
  }
  return parsed.data;
}

export type Note = typeof notes.$inferSelect;

export async function listNotes(ownerId: string): Promise<Note[]> {
  return getDb().select().from(notes).where(eq(notes.ownerId, ownerId)).orderBy(desc(notes.createdAt));
}

export async function createNote(ownerId: string, body: string): Promise<Note> {
  const [note] = await getDb().insert(notes).values({ ownerId, body }).returning();
  return note;
}
