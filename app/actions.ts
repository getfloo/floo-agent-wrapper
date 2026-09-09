"use server";

import { revalidatePath } from "next/cache";
import { getDb } from "@/db";
import { notes } from "@/db/schema";
import { syncUser } from "@/db/users";
import { getIdentity } from "@/lib/identity";

export async function addNote(formData: FormData): Promise<void> {
  const identity = await getIdentity();
  const body = formData.get("body");
  if (typeof body !== "string" || !body.trim() || body.length > 5000) {
    throw new Error("Write a note between 1 and 5,000 characters.");
  }
  await syncUser(identity);
  await getDb().insert(notes).values({ userId: identity.id, body: body.trim() });
  revalidatePath("/");
}
