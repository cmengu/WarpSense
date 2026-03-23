import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {
    root: process.cwd(),
  },
  async redirects() {
    return [
      { source: "/seagull", destination: "/dashboard", permanent: false },
      {
        source: "/compare/live",
        destination:
          "/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001",
        permanent: false,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/manifest.json",
        headers: [
          { key: "Content-Type", value: "application/manifest+json" },
        ],
      },
    ];
  },
};

export default nextConfig;
