import type { NextConfig } from "next";

const config: NextConfig = {
  output: process.env.DEMANDTWIN_STANDALONE === "1" ? "standalone" : undefined,
  devIndicators: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${process.env.API_ORIGIN ?? "http://127.0.0.1:8000"}/api/v1/:path*` }];
  },
};
export default config;
