import { syncUser } from "@/db/users";
import { getIdentity } from "@/lib/identity";
import { MAX_NOTE_LENGTH, listNotes } from "@/lib/notes";
import { addNote } from "./actions";

export const dynamic = "force-dynamic";

export default async function Home() {
  const identity = await getIdentity();
  await syncUser(identity);
  const userNotes = await listNotes(identity.id);

  return (
    <main className="mx-auto max-w-2xl px-6 py-12 sm:py-20">
      <header className="mb-10 border-b pb-8">
        <p className="mb-3 text-sm text-muted">Signed in as {identity.email}</p>
        <a href="/api-docs" className="text-sm font-medium text-accent underline underline-offset-4 hover:text-accent-hover">API docs</a>
        <h1 className="text-3xl font-semibold tracking-tight">Welcome, {identity.name || identity.email}.</h1>
        <p className="mt-3 text-muted">A little space for your ideas. Your notes are just for you.</p>
      </header>

      <form action={addNote} className="mb-12">
        <label htmlFor="body" className="mb-3 block text-sm font-medium">What’s on your mind?</label>
        <textarea id="body" name="body" required maxLength={MAX_NOTE_LENGTH} rows={4}
          placeholder="Write your first thought…"
          className="block w-full resize-y text-base placeholder:text-muted" />
        <button type="submit"
          className="mt-3 rounded-sm bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent-hover">
          Add note
        </button>
      </form>

      <section aria-labelledby="notes-heading">
        <h2 id="notes-heading" className="mb-4 text-lg font-semibold">Your notes <span className="ml-1 font-normal text-muted">({userNotes.length})</span></h2>
        {userNotes.length === 0 ? (
          <p className="rounded-md border border-dashed p-8 text-center text-muted">No notes yet. Add one above to get started.</p>
        ) : (
          <ul className="space-y-3">
            {userNotes.map((note) => (
              <li key={note.id} className="rounded-md border bg-panel p-5">
                <p className="whitespace-pre-wrap wrap-anywhere leading-relaxed">{note.body}</p>
                <time dateTime={note.createdAt.toISOString()} className="mt-4 block text-xs text-muted">
                  {note.createdAt.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
