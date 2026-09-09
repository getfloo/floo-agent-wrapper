import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: vi.fn() }));

import { headers } from "next/headers";
import { getIdentity } from "../lib/identity";

const gatewayHeaders = {
  "X-Floo-User-Id": "user-123",
  "X-Floo-User-Email": "pat@example.com",
  "X-Floo-User-Name": "Pat",
  "X-Floo-User-Role": "admin",
};

function useHeaders(values: Headers) {
  vi.mocked(headers).mockResolvedValue(values as Awaited<ReturnType<typeof headers>>);
}

beforeEach(() => vi.clearAllMocks());

describe("gateway identity", () => {
  it("reads all four case-insensitive gateway headers", async () => {
    useHeaders(new Headers(gatewayHeaders));
    await expect(getIdentity()).resolves.toEqual({
      id: "user-123", email: "pat@example.com", name: "Pat", role: "admin",
    });
  });

  it.each(Object.keys(gatewayHeaders))("rejects a missing %s", async (header) => {
    const values = new Headers(gatewayHeaders);
    values.delete(header);
    useHeaders(values);
    await expect(getIdentity()).rejects.toThrow(`Missing ${header}`);
  });

  it.each(Object.keys(gatewayHeaders))("rejects a blank %s", async (header) => {
    useHeaders(new Headers({ ...gatewayHeaders, [header]: "  " }));
    await expect(getIdentity()).rejects.toThrow("did not come through the floo gateway");
  });

  it.each(["admin", "member", "viewer", "custom-role"])("preserves the gateway role %s", async (role) => {
    useHeaders(new Headers({ ...gatewayHeaders, "X-Floo-User-Role": role }));
    expect((await getIdentity()).role).toBe(role);
  });

  it("explains how to run a request with no gateway headers", async () => {
    useHeaders(new Headers());
    await expect(getIdentity()).rejects.toThrow("Use floo dev locally and accounts mode when deployed");
  });
});
