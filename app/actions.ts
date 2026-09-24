"use server";

import { revalidatePath } from "next/cache";
import { syncUser } from "@/db/users";
import { getIdentity } from "@/lib/identity";
import { createNote, parseNoteInput } from "@/lib/notes";

export async function addNote(formData: FormData): Promise<void> {
  const user = await getIdentity();
  const { body } = parseNoteInput({ body: formData.get("body") });
  await syncUser(user);
  await createNote(user.id, body);
  revalidatePath("/");
}
