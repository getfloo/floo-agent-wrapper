import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // AGENTS.md is this repo's agent guide; stop `next dev` from appending its own block,
  // which leaves the tree dirty and makes `floo deploy` refuse to run.
  agentRules: false,
};

export default nextConfig;
