import { callerFrom } from "@/lib/identity";
import { openApiDocument } from "@/lib/openapi";
import { operations as notes } from "../notes/openapi";

// Every /api route's operations, in one list. tests/openapi.test.ts fails when a
// route handler is missing from it. Served under /api, so the gateway requires
// the same API key as every other endpoint; the spec is never public.
const operations = [...notes];

export function GET(request: Request): Response {
  callerFrom(request.headers);
  return Response.json(openApiDocument(operations));
}
