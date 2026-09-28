"use client";

import { ApiReferenceReact } from "@scalar/api-reference-react";
import "@scalar/api-reference-react/style.css";
import type { openApiDocument } from "@/lib/openapi";

export function Reference({ document }: { document: ReturnType<typeof openApiDocument> }) {
  return <ApiReferenceReact configuration={{ content: document }} />;
}
