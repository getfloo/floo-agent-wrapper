"use client";

import { ApiReferenceReact } from "@scalar/api-reference-react";
import "@scalar/api-reference-react/style.css";
import type { openApiDocument } from "@/lib/openapi";

export function Reference({ document }: { document: ReturnType<typeof openApiDocument> }) {
  // Scalar sends "Try it" requests through proxy.scalar.com and loads fonts from
  // fonts.scalar.com by default; keep a pasted API key and visitors on this origin.
  return <ApiReferenceReact configuration={{ content: document, proxyUrl: "", withDefaultFonts: false }} />;
}
