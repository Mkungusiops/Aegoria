import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // produces a lean self-contained server for the Docker image
  // Pin the monorepo root so the standalone build traces the right node_modules
  // (silences the multi-lockfile root-inference warning and fixes Docker tracing).
  outputFileTracingRoot: repoRoot,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  env: {
    // Point the console at the control-plane API. When unset, the console serves
    // realistic fixtures from lib/data so the UI always runs standalone.
    AEGORIA_API_URL: process.env.AEGORIA_API_URL ?? "",
  },
};

export default nextConfig;
