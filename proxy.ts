import { NextResponse, type NextRequest } from "next/server";

// floo sends GET / with X-Floo-Probe to keep the app warm and to check a deploy.
// The probe carries no user, so answer it before any page renders. Only floo can
// send this header: the gateway strips X-Floo-* from every visitor's request.
export function proxy(request: NextRequest): NextResponse {
  if (request.headers.has("x-floo-probe")) {
    return new NextResponse(null, { status: 204 });
  }
  return NextResponse.next();
}

export const config = { matcher: "/" };
