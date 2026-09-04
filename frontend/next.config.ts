import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Ollama の分析には30秒以上かかることがあるため、rewrite の
    // デフォルト値（30秒）より長くバックエンドの応答を待つ。
    proxyTimeout: 180_000,
  },
  async rewrites () {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      }
    ]
  }
};

export default nextConfig;
