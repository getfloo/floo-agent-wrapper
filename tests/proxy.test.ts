import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { proxy } from "../proxy";

describe("proxy", () => {
  it("answers floo's probe without rendering the page", () => {
    const response = proxy(new NextRequest("https://app.test/", { headers: { "X-Floo-Probe": "1" } }));
    expect(response.status).toBe(204);
  });

  it("passes every other request through", () => {
    const response = proxy(new NextRequest("https://app.test/"));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });
});
