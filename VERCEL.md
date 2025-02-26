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

## Serverless Compatibility Layer

The application includes a serverless compatibility layer to handle common issues with serverless deployments, particularly focusing on file system access and error handling:

### 1. Dowse Logger Patching

The Dowse library tries to create log files by default, which fails in Vercel's read-only filesystem. We've implemented a comprehensive patching system:

#### api/index.py Monkey Patch

This patch is applied before any imports to prevent file system access errors:

```python
# CRITICAL: Monkey patch Dowse's logging module BEFORE importing anything else
def patch_dowse_modules():
    """
    Patch Dowse's logger module before it gets imported to prevent file system access.
    Must be called before any imports that might trigger Dowse's logger initialization.
    """
    import importlib.util
    import types
    import logging
    import sys

    # Create a default logger that only writes to stdout
    logger = logging.getLogger("dowse")
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add a stdout handler only
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)

    # Create a fake module to replace dowse.logger
    mock_logger_module = types.ModuleType("dowse.logger")
    mock_logger_module.logger = MockLogger()  # Custom logger class

    # Monkey patch sys.modules
    sys.modules["dowse.logger"] = mock_logger_module

    return logger

# Apply the patch before importing anything from Dowse
patch_dowse_modules()

# Now it's safe to import the app
from app.main import app
```

### 2. Serverless Middleware

A middleware layer catches and handles common serverless errors:

```python
class ServerlessCompatibilityMiddleware(BaseHTTPMiddleware):
    """Middleware for handling common serverless deployment issues."""

    async def dispatch(self, request: Request, call_next):
        try:
            # Call the next middleware/route handler
            response = await call_next(request)
            return response
        except OSError as e:
            # Catch file system errors
            if "Read-only file system" in str(e):
                logger.error(f"Read-only file system error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Server error: Unable to write to file system",
                        "error_type": "read_only_fs",
                        "error": str(e)
                    }
                )
            # Re-raise other OS errors
            raise
        except Exception as e:
            # Log all other exceptions
            logger.error(f"Unhandled exception: {e}")
            logger.error(traceback.format_exc())
            raise
```

### 3. Configuration for Serverless Environments

In `app/main.py`, the middleware is conditionally applied in serverless environments:

```python
# Only apply in Vercel environment
if os.environ.get("VERCEL", "0") == "1":
    try:
        from api.middleware import add_serverless_compatibility
        app = add_serverless_compatibility(app)
        logger.info("Added serverless compatibility middleware")
    except ImportError:
        logger.warning("Serverless compatibility middleware not found, skipping")
    except Exception as e:
        logger.error(f"Error adding serverless compatibility middleware: {e}")
```

### 4. Logging Configuration

The logging configuration in `app/utils/configure_logging.py` is adapted for serverless environments:

```python
# Configure file handler if LOG_FILE is set
log_file = os.environ.get("LOG_FILE")
if log_file:
    # Check if we're in a serverless environment (Vercel)
    is_serverless = os.environ.get("VERCEL", "").lower() == "1"

    # If in serverless, use /tmp directory which is writable
    if is_serverless and not log_file.startswith("/tmp/"):
        log_file = f"/tmp/{os.path.basename(log_file)}"
```

## Additional Vercel Environment Variables

For proper serverless compatibility, ensure these environment variables are set:

- `VERCEL`: Set to "1" to enable serverless compatibility features
- `ENABLE_FILE_LOGGING`: Set to "false" to disable file logging attempts (recommended for serverless)
- `LOG_LEVEL`: Set to desired log level (INFO, DEBUG, WARNING, ERROR)

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

2. **Run Compatibility Test**: Run the `test_vercel_compatibility.py` script to verify your application is ready for Vercel deployment:

   ```bash
   python test_vercel_compatibility.py
   ```

   This script checks for common issues in serverless environments, such as:

   - File system access in read-only directories
   - Module import compatibility
   - `/tmp` directory access

3. **Incremental Deployments**: Make small changes and deploy frequently to catch issues early.

4. **Environment Isolation**: Use different environments (production, preview, development) for testing.

5. **Logging**: Use structured logging and avoid file-based logging in serverless environments.

6. **Caching**: Implement caching for expensive operations like token price lookups.

7. **Error Handling**: Add comprehensive error handling for all API endpoints.

8. **Cold Start Optimization**: Minimize dependencies and code size to reduce cold start times.

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

### Common Serverless Errors

#### Read-only File System

If you encounter errors like:

```
OSError: [Errno 30] Read-only file system: '/var/task/info.log'
```

This indicates that some code is trying to write to the file system, which is not allowed in Vercel's serverless environment:

1. Check that the Dowse logger patch is properly applied
2. Ensure all file operations use the `/tmp` directory
3. Set `ENABLE_FILE_LOGGING=false` in your environment variables

#### Memory Limit Exceeded

If your function crashes with memory errors:

1. Check the memory allocation in `vercel.json` (increase if necessary)
2. Look for memory leaks or large object allocations
3. Consider splitting complex operations into separate functions

#### Execution Timeout

If functions time out (504 errors):

1. Check the `maxDuration` setting in `vercel.json`
2. Optimize slow operations, especially external API calls
3. Implement caching for expensive operations
4. Add more detailed logging to identify bottlenecks

### Deployment Verification

After deployment, test these endpoints to verify functionality:

- `/api/health`: Should return status information
- `/api/ping`: Should return a simple response with timestamp
