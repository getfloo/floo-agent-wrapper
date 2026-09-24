import { z } from "zod";
import { NoteInput } from "@/lib/notes";
import { ApiError, type Operation } from "@/lib/openapi";

/** A note as the API returns it. */
export const NoteJson = z.object({
  id: z.uuid(),
  ownerId: z.string().meta({ description: "The API consumer or user that created the note." }),
  body: z.string(),
  createdAt: z.iso.datetime(),
});

// The contract for ./route.ts. Listed in app/api/openapi.json/route.ts; the
// tests fail if a handler is missing here or a response stops matching.
export const operations: Operation[] = [
  {
    method: "get",
    path: "/api/notes",
    operationId: "listNotes",
    summary: "List the caller's notes, newest first.",
    responses: { 200: { description: "The caller's notes.", schema: z.object({ notes: z.array(NoteJson) }) } },
  },
  {
    method: "post",
    path: "/api/notes",
    operationId: "createNote",
    summary: "Create a note owned by the caller.",
    request: NoteInput,
    responses: {
      201: { description: "The created note.", schema: z.object({ note: NoteJson }) },
      400: { description: "The body is not JSON or the note is empty or too long.", schema: ApiError },
    },
  },
];
