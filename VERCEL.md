# Vercel Deployment Guide for Pointless

This document provides guidance on deploying the Pointless AI Crypto Assistant to Vercel's serverless platform.

## Deployment Structure

The application uses a hybrid deployment structure:

- Backend: Python FastAPI application deployed as a serverless function
- Frontend: Next.js application served through Vercel's Next.js platform

## Key Configuration Files

### 1. vercel.json

This file configures how Vercel builds and deploys your application:

```json
{
  "version": 2,
  "buildCommand": "chmod +x vercel.build.sh && ./vercel.build.sh",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxDuration": 90,
        "memory": 1024,
        "runtime": "python3.12",
        "handler": "app",
        "includeFiles": [
          "app/**",
          "api/**",
          "src/**",
          "requirements.txt",
          "*.py",
          ".env*"
        ],
        "excludeFiles": [
          "**/*.test.py",
          "**/*_test.py",
          "test_*.py",
          "tests/**",
          ".pytest_cache/**",
          "__pycache__/**",
          ".coverage",
          ".env.test",
          "test_redis_simple.py",
          "test_redis_ssl.py",
          "test_redis_upstash.py"
        ]
      }
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/next"
    }
  ],
  "routes": [
    {
      "src": "/favicon.ico",
      "dest": "/frontend/public/favicon.ico"
    },
    {
      "src": "/icon.png",
      "dest": "/frontend/public/icon.png"
    },
    {
      "src": "/apple-icon.png",
      "dest": "/frontend/public/apple-icon.png"
    },
    {
      "src": "/manifest.json",
      "dest": "/frontend/public/manifest.json"
    },
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py",
      "headers": {
        "Cache-Control": "s-maxage=0"
      }
    },
    {
      "handle": "filesystem"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ],
  "regions": ["iad1"],
  "env": {
    "PYTHONUNBUFFERED": "1",
    "PYTHONPATH": ".",
    "PYTHONIOENCODING": "utf-8",
    "QUICKNODE_ENDPOINT": "https://api.kyberswap.com",
    "VERCEL": "1",
    "LOG_LEVEL": "INFO",
    "ENABLE_FILE_LOGGING": "false"
  }
}
```

### 2. vercel.build.sh

This script runs during the build phase to set up the Python environment:

```bash
#!/bin/bash

# Set NODE_ENV to production
export NODE_ENV=production

# Clear any existing NEXT_PUBLIC_API_URL
unset NEXT_PUBLIC_API_URL

# Skip tests during the build
export SKIP_TESTS=1

# Install Python packages from requirements.txt
pip install -r requirements.txt

# Install additional packages with specific versions if needed
pip install dowse==0.1.6.post1 emp-agents==0.3.0 eth-rpc-py==0.1.26

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Create necessary directories if they don't exist
mkdir -p app/services
mkdir -p app/api/routes
mkdir -p app/utils
mkdir -p app/models
mkdir -p app/agents
mkdir -p api

# Ensure the script exits with success
exit 0
```

### 3. .vercelignore

This file tells Vercel what files to ignore during deployment:

```
tests/
test_*.py
**/*.test.py
**/*_test.py
.pytest_cache/
__pycache__/
.coverage
.env.test
test_redis_simple.py
test_redis_ssl.py
test_redis_upstash.py
```

### 4. runtime.txt

Specifies the Python version:

```
python-3.12
```

## Environment Variables

These environment variables should be set in the Vercel project settings:

- `ALCHEMY_KEY`: API key for Alchemy service
- `COINGECKO_API_KEY`: API key for CoinGecko service
- `MORALIS_API_KEY`: API key for Moralis service
- `ZEROX_API_KEY`: API key for 0x API
- `REDIS_URL`: URL for Upstash Redis database
- `NEXT_PUBLIC_API_URL`: URL for the API in production (automatically set by Vercel)

## Common Issues and Solutions

### 1. Tests Running During Build

If tests are running during the build process:

- Make sure `.vercelignore` includes all test files and directories
- Set `SKIP_TESTS=1` in the build script

### 2. Missing Modules

If you encounter "Module not found" errors:

- Check that all required modules are in `requirements.txt`
- Verify that `vercel.build.sh` is creating necessary directories

### 3. Functions vs Builds Conflict

Vercel requires using either "functions" or "builds" configuration, but not both:

- For Python applications with Next.js, use "builds" for defining sources
- For function-specific settings (memory, maxDuration), ensure they're in the correct location

### 4. Redis Connection Issues

If Redis connection fails in production:

- Verify the `REDIS_URL` environment variable is set correctly
- Check that Redis permits connections from Vercel's IP range
- Ensure the connection uses TLS for security

## Deployment Best Practices

1. **Test Locally First**: Use `vercel dev` to test your application locally before deploying.

2. **Incremental Deployments**: Make small changes and deploy frequently to catch issues early.

3. **Environment Isolation**: Use different environments (production, preview, development) for testing.

4. **Logging**: Use structured logging and avoid file-based logging in serverless environments.

5. **Caching**: Implement caching for expensive operations like token price lookups.

6. **Error Handling**: Add comprehensive error handling for all API endpoints.

7. **Cold Start Optimization**: Minimize dependencies and code size to reduce cold start times.

## Troubleshooting

### Log Access

Access logs through the Vercel dashboard:

1. Go to your project
2. Click on the deployment
3. Navigate to "Functions" tab
4. Click on a function to view its logs

### Common Error Codes

- **500**: Internal server error, check function logs
- **504**: Function execution timed out, consider increasing maxDuration
- **404**: Route or function not found, check routing configuration
- **403**: Forbidden, check authentication settings

### Deployment Verification

After deployment, test these endpoints to verify functionality:

- `/api/health`: Should return status information
- `/api/ping`: Should return a simple response with timestamp
