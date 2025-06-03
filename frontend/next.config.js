/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable static optimization for Web3 app
  output: "standalone",
  webpack: (config) => {
    config.resolve.fallback = {
      fs: false,
      net: false,
      tls: false,
      // Add fallbacks for Web3 dependencies
      crypto: false,
      stream: false,
      assert: false,
      http: false,
      https: false,
      os: false,
      url: false,
      zlib: false,
    };
    return config;
  },
  // For monorepo structure, we use rewrites instead of env variables
  async rewrites() {
    return process.env.NODE_ENV === "development"
      ? [
          {
            source: "/api/:path*",
            destination: "http://localhost:8000/api/:path*",
          },
          {
            source: "/debug/:path*",
            destination: "http://localhost:8000/debug/:path*",
          },
        ]
      : [];
  },
};

module.exports = nextConfig;
