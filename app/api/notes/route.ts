import { callerFrom } from "@/lib/identity";
import { InvalidNote, createNote, listNotes, parseNoteBody } from "@/lib/notes";

// The gateway serves /api to callers holding an app API key (see [[routes]] in
// floo.app.toml). It has already verified the key; this handler only reads who
// the caller is. A signed-in user's browser can reach /api too, so both kinds
// of caller get their own notes, keyed by the id the gateway asserted.

export async function GET(request: Request): Promise<Response> {
  const caller = callerFrom(request.headers);
  return Response.json({ notes: await listNotes(caller.id) });
}

export async function POST(request: Request): Promise<Response> {
  const caller = callerFrom(request.headers);
  let body: unknown;
  try {
    body = ((await request.json()) as { body?: unknown }).body;
  } catch {
    return Response.json({ error: 'Send JSON like {"body": "text"}.' }, { status: 400 });
  }
  try {
    const note = await createNote(caller.id, parseNoteBody(body));
    return Response.json({ note }, { status: 201 });
  } catch (error) {
    if (error instanceof InvalidNote) {
      return Response.json({ error: error.message }, { status: 400 });
    }
    throw error;
  }
}
