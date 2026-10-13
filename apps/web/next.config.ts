import path from "node:path";
import type { NextConfig } from "next";

// Le navigateur appelle /api/* ; Next relaie vers l'API FastAPI (jamais d'appel direct depuis le client).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Export statique (D01) : NEXT_PUBLIC_STATIC_EXPORT=1, pages générées au build depuis l'API locale.
const STATIC = process.env.NEXT_PUBLIC_STATIC_EXPORT === "1";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const config: NextConfig = {
  output: STATIC ? "export" : "standalone",
  ...(STATIC ? { basePath: BASE_PATH, trailingSlash: true, images: { unoptimized: true } } : {}),
  outputFileTracingRoot: path.join(__dirname),
  poweredByHeader: false,
  ...(STATIC
    ? {}
    : {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
        },
      }),
};

export default config;
