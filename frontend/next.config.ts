import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "standalone",
  basePath: basePath || undefined,
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Explicit Django routes only — /api/auth/* stays with NextAuth
    return [
      { source: "/api/agents/:path*",    destination: `${apiUrl}/api/agents/:path*` },
      { source: "/api/decisions/:path*", destination: `${apiUrl}/api/decisions/:path*` },
      { source: "/api/incidents/:path*", destination: `${apiUrl}/api/incidents/:path*` },
      { source: "/api/audit/:path*",     destination: `${apiUrl}/api/audit/:path*` },
      { source: "/api/domains/:path*",   destination: `${apiUrl}/api/domains/:path*` },
      { source: "/api/v1/:path*",          destination: `${apiUrl}/api/v1/:path*` },
      { source: "/api/eraya-auth/:path*", destination: `${apiUrl}/api/eraya-auth/:path*` },
    ];
  },
};

export default nextConfig;
