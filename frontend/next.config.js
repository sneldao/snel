/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    config.resolve.fallback = { fs: false, net: false, tls: false };
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
