import "server-only";
import { headers } from "next/headers";

export type Identity = {
  id: string;
  email: string;
  name: string;
  role: string;
};

// These headers are trusted only while the floo gateway is the sole ingress.
export async function getIdentity(): Promise<Identity> {
  const requestHeaders = await headers();
  const required = (header: string): string => {
    const value = requestHeaders.get(header)?.trim();
    if (!value) {
      throw new Error(
        `Missing ${header}: this request did not come through the floo gateway. Use floo dev locally and accounts mode when deployed.`,
      );
    }
    return value;
  };

  return {
    id: required("X-Floo-User-Id"),
    email: required("X-Floo-User-Email"),
    name: required("X-Floo-User-Name"),
    role: required("X-Floo-User-Role"),
  };
}
