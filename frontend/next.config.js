/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use standalone for local development, but not for Netlify
  ...(process.env.NETLIFY ? {} : { output: "standalone" }),
  // Fix workspace root detection
  outputFileTracingRoot: require('path').join(__dirname, '../'),
  // Turbopack configuration for Node.js module browser fallbacks
  // Unlike webpack's `false`, Turbopack requires explicit empty module resolution
  turbopack: {
    resolveAlias: {
      fs: { browser: './node_modules/next/dist/compiled/empty' },
      net: { browser: './node_modules/next/dist/compiled/empty' },
      tls: { browser: './node_modules/next/dist/compiled/empty' },
      crypto: { browser: './node_modules/next/dist/compiled/empty' },
      stream: { browser: './node_modules/next/dist/compiled/empty' },
      assert: { browser: './node_modules/next/dist/compiled/empty' },
      http: { browser: './node_modules/next/dist/compiled/empty' },
      https: { browser: './node_modules/next/dist/compiled/empty' },
      os: { browser: './node_modules/next/dist/compiled/empty' },
      url: { browser: './node_modules/next/dist/compiled/empty' },
      zlib: { browser: './node_modules/next/dist/compiled/empty' },
      'sodium-native': { browser: './node_modules/next/dist/compiled/empty' },
      'require-addon': { browser: './node_modules/next/dist/compiled/empty' },
      'node-gyp-build': { browser: './node_modules/next/dist/compiled/empty' },
      bindings: { browser: './node_modules/next/dist/compiled/empty' },
      child_process: { browser: './node_modules/next/dist/compiled/empty' },
      worker_threads: { browser: './node_modules/next/dist/compiled/empty' },
      perf_hooks: { browser: './node_modules/next/dist/compiled/empty' },
      async_hooks: { browser: './node_modules/next/dist/compiled/empty' },
    },
  },
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
      // Add fallbacks for Axelar SDK dependencies
      "sodium-native": false,
      "require-addon": false,
      "node-gyp-build": false,
      bindings: false,
      child_process: false,
      worker_threads: false,
      perf_hooks: false,
      async_hooks: false,
    };

    // Ignore specific modules that cause issues with Axelar SDK
    config.externals = config.externals || [];
    config.externals.push({
      "sodium-native": "sodium-native",
      "require-addon": "require-addon",
      "node-gyp-build": "node-gyp-build",
    });

    return config;
  },
  // For monorepo structure, we use rewrites instead of env variables
  async rewrites() {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return process.env.NODE_ENV === "development"
      ? [
        {
          source: "/api/:path*",
          destination: `${apiBaseUrl}/api/:path*`,
        },
        {
          source: "/debug/:path*",
          destination: `${apiBaseUrl}/debug/:path*`,
        },
      ]
      : [];
  },
};

module.exports = nextConfig;
