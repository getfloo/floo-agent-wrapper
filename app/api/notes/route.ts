import { callerFrom } from "@/lib/identity";
import { InvalidNote, createNote, listNotes, parseNoteInput } from "@/lib/notes";

// The gateway serves /api only to callers holding an app API key with the "api"
// scope ([[routes]] in floo.app.toml) and has already verified the key. Notes
// belong to the caller id it asserted. The contract is in ./openapi.ts.

export async function GET(request: Request): Promise<Response> {
  const caller = callerFrom(request.headers);
  return Response.json({ notes: await listNotes(caller.id) });
}

export async function POST(request: Request): Promise<Response> {
  const caller = callerFrom(request.headers);
  let input: unknown;
  try {
    input = await request.json();
  } catch {
    return Response.json({ error: 'Send JSON like {"body": "text"}.' }, { status: 400 });
  }
  try {
    const { body } = parseNoteInput(input);
    return Response.json({ note: await createNote(caller.id, body) }, { status: 201 });
  } catch (error) {
    if (error instanceof InvalidNote) {
      return Response.json({ error: error.message }, { status: 400 });
    }
    throw error;
  }
}
