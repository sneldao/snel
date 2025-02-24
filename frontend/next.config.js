/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    config.resolve.fallback = { fs: false, net: false, tls: false };
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
        ]
      : [
          {
            source: "/api/:path*",
            destination: "/api/:path*",
          },
        ];
  },
};

module.exports = nextConfig;
