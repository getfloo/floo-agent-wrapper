import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: vi.fn() }));
vi.mock("@/db", () => ({ getDb: () => { throw new Error("tests never open a database"); } }));
vi.mock("@/lib/notes", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/notes")>()),
  listNotes: vi.fn(),
  createNote: vi.fn(),
}));

import { GET, POST } from "../app/api/notes/route";
import { createNote, listNotes } from "../lib/notes";

const keyHeaders = {
  "X-Floo-Auth-Method": "api_key",
  "X-Floo-Api-Consumer-Id": "consumer-9",
  "X-Floo-Api-Key-Id": "key-42",
  "X-Floo-Api-Key-Scopes": "api",
};

const note = { id: "n1", ownerId: "consumer-9", body: "hello", createdAt: new Date("2026-01-01T00:00:00Z") };

beforeEach(() => vi.clearAllMocks());

describe("GET /api/notes", () => {
  it("lists the key consumer's own notes", async () => {
    vi.mocked(listNotes).mockResolvedValue([note]);
    const response = await GET(new Request("http://app/api/notes", { headers: keyHeaders }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ notes: [{ ...note, createdAt: note.createdAt.toISOString() }] });
    expect(listNotes).toHaveBeenCalledWith("consumer-9");
  });

  it("refuses a request that did not come through the gateway", async () => {
    await expect(GET(new Request("http://app/api/notes"))).rejects.toThrow("did not come through the floo gateway");
    expect(listNotes).not.toHaveBeenCalled();
  });
});

describe("POST /api/notes", () => {
  const post = (body: BodyInit) =>
    POST(new Request("http://app/api/notes", { method: "POST", headers: keyHeaders, body }));

  it("creates a note for the key consumer", async () => {
    vi.mocked(createNote).mockResolvedValue(note);
    const response = await post(JSON.stringify({ body: "  hello " }));
    expect(response.status).toBe(201);
    expect(createNote).toHaveBeenCalledWith("consumer-9", "hello");
  });

  it("answers invalid input with 400 and the same message the form shows", async () => {
    const response = await post(JSON.stringify({ body: "" }));
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "Write a note between 1 and 5,000 characters." });
    expect(createNote).not.toHaveBeenCalled();
  });

  it("answers a non-JSON body with 400", async () => {
    const response = await post("not json");
    expect(response.status).toBe(400);
    expect(createNote).not.toHaveBeenCalled();
  });
});
