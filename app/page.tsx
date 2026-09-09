import { desc, eq } from "drizzle-orm";
import { getDb } from "@/db";
import { notes } from "@/db/schema";
import { syncUser } from "@/db/users";
import { getIdentity } from "@/lib/identity";
import { addNote } from "./actions";

export const dynamic = "force-dynamic";

export default async function Home() {
  const identity = await getIdentity();
  await syncUser(identity);
  const userNotes = await getDb().select().from(notes)
    .where(eq(notes.userId, identity.id)).orderBy(desc(notes.createdAt));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12 sm:py-20">
      <header className="mb-10 border-b border-stone-200 pb-8">
        <p className="mb-3 text-sm text-stone-500">Signed in as {identity.email}</p>
        <h1 className="text-3xl font-semibold tracking-tight">Welcome, {identity.name}.</h1>
        <p className="mt-3 text-stone-600">A little space for your ideas. Your notes are just for you.</p>
      </header>

      <form action={addNote} className="mb-12">
        <label htmlFor="body" className="mb-3 block text-sm font-medium">What’s on your mind?</label>
        <textarea id="body" name="body" required maxLength={5000} rows={4}
          placeholder="Write your first thought…"
          className="block w-full resize-y rounded-xl border border-stone-300 bg-white p-4 text-base placeholder:text-stone-400 focus:outline-2 focus:outline-offset-2 focus:outline-stone-700" />
        <button type="submit"
          className="mt-3 rounded-lg bg-stone-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-stone-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-900">
          Add note
        </button>
      </form>

      <section aria-labelledby="notes-heading">
        <h2 id="notes-heading" className="mb-4 text-lg font-semibold">Your notes <span className="ml-1 font-normal text-stone-500">({userNotes.length})</span></h2>
        {userNotes.length === 0 ? (
          <p className="rounded-xl border border-dashed border-stone-300 p-8 text-center text-stone-500">No notes yet. Add one above to get started.</p>
        ) : (
          <ul className="space-y-3">
            {userNotes.map((note) => (
              <li key={note.id} className="rounded-xl border border-stone-200 bg-white p-5">
                <p className="whitespace-pre-wrap wrap-anywhere leading-relaxed">{note.body}</p>
                <time dateTime={note.createdAt.toISOString()} className="mt-4 block text-xs text-stone-500">
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
