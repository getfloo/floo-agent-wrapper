"use client";

import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";
import type { openApiDocument } from "@/lib/openapi";

export function Reference({ document }: { document: ReturnType<typeof openApiDocument> }) {
  return <SwaggerUI spec={document} />;
}
