import "server-only";
import type { Identity } from "@/lib/identity";
import { getDb } from "./index";
import { users } from "./schema";

export async function syncUser(identity: Identity) {
  await getDb().insert(users).values(identity).onConflictDoUpdate({
    target: users.id,
    set: {
      email: identity.email,
      name: identity.name,
      role: identity.role,
      updatedAt: new Date(),
    },
  });
}
