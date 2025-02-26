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
pip install dowse==0.1.6.post1 emp-agents==0.3.0 eth-rpc-py==0.1.26 pydantic_settings==2.2.1

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

## Required Dependencies

The application requires the following key dependencies:

- `pydantic`: Data validation library
- `pydantic_settings`: Settings management for pydantic (required for app/config/settings.py)
- `fastapi`: Web framework
- `dowse`: Core library for crypto operations
- `emp-agents`: Agent framework for natural language processing

If you encounter a `ModuleNotFoundError` for any of these dependencies, make sure they are properly installed in your `vercel.build.sh` script:

```bash
# Install additional packages with specific versions if needed
pip install dowse==0.1.6.post1 emp-agents==0.3.0 eth-rpc-py==0.1.26 pydantic_settings==2.2.1
```

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
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

logger = logging.getLogger(__name__)

class ServerlessCompatibilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except OSError as e:
            # Check if this is a read-only filesystem error
            if "Read-only file system" in str(e):
                logger.error(f"Serverless filesystem error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Serverless environment error",
                        "message": "The application attempted to write to the filesystem in a read-only environment",
                        "detail": str(e)
                    }
                )
            # Re-raise other OS errors
            raise
        except Exception as e:
            logger.exception(f"Unhandled exception in request: {e}")
            raise
```

### 3. Comprehensive Dowse Logger Patch

A more comprehensive patch for the Dowse logger is implemented in `app/utils/dowse_logger_patch.py`:

```python
import logging
import os
import sys
import types

def patch_dowse_logger():
    """
    Patch Dowse's logger module to prevent file system access in serverless environments.
    This function creates a mock logger class that mimics the Dowse logger's methods
    but only logs to stdout, avoiding file system operations.
    """
    # Check if we're in a serverless environment
    is_serverless = os.environ.get("VERCEL", "").lower() == "1"
    enable_file_logging = os.environ.get("ENABLE_FILE_LOGGING", "").lower() == "true"

    # Only disable file logging in serverless environments unless explicitly enabled
    if is_serverless and not enable_file_logging:
        # Create a mock logger class
        class MockLogger:
            def __init__(self):
                self._logger = logging.getLogger("dowse")
                self._logger.setLevel(logging.INFO)

                # Remove any existing handlers
                for handler in self._logger.handlers[:]:
                    # Only remove FileHandlers
                    if isinstance(handler, logging.FileHandler):
                        self._logger.removeHandler(handler)

                # Ensure we have a stdout handler
                has_stdout_handler = False
                for handler in self._logger.handlers:
                    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                        has_stdout_handler = True
                        break

                if not has_stdout_handler:
                    handler = logging.StreamHandler(sys.stdout)
                    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                    handler.setFormatter(formatter)
                    self._logger.addHandler(handler)

                self._logger.info("File logging disabled")

            def debug(self, msg, *args, **kwargs):
                self._logger.debug(msg, *args, **kwargs)

            def info(self, msg, *args, **kwargs):
                self._logger.info(msg, *args, **kwargs)

            def warning(self, msg, *args, **kwargs):
                self._logger.warning(msg, *args, **kwargs)

            def error(self, msg, *args, **kwargs):
                self._logger.error(msg, *args, **kwargs)

            def critical(self, msg, *args, **kwargs):
                self._logger.critical(msg, *args, **kwargs)

            def exception(self, msg, *args, **kwargs):
                self._logger.exception(msg, *args, **kwargs)

        # Create a mock module
        mock_logger_module = types.ModuleType("dowse.logger")
        mock_logger_module.logger = MockLogger()

        # Monkey patch sys.modules
        sys.modules["dowse.logger"] = mock_logger_module

        logging.getLogger("app").info("Patched dowse.logger in sys.modules")
```

## Testing Serverless Compatibility

Before deploying to Vercel, you can test serverless compatibility locally using the provided test script:

```bash
# Make the test script executable
chmod +x tests/test_serverless.py

# Run the test
poetry run python tests/test_serverless.py
```

The test script checks:

1. Python version compatibility
2. Read-only filesystem handling
3. Dowse logger patching
4. Application startup in a simulated serverless environment
5. Health check endpoint functionality
6. Installed packages verification (including pydantic_settings)

## Common Serverless Errors

### Missing Dependencies

If you encounter an error like:

```
ModuleNotFoundError: No module named 'pydantic_settings'
```

This indicates that a required package is missing from your deployment. To fix this:

1. Add the missing package to your `requirements.txt` file
2. Explicitly install it in your `vercel.build.sh` script:
   ```bash
   pip install pydantic_settings==2.2.1
   ```
3. Check the "Required Dependencies" section above for common packages

### Checking Installed Packages

To verify which packages are installed in your Vercel deployment:

1. Add this line to your `vercel.build.sh` script to output installed packages:

   ```bash
   pip freeze > installed_packages.txt
   ```

2. Check the build logs after deployment to view the contents of this file, or

3. Create an API endpoint to list installed packages:

   ```python
   @app.get("/api/debug/packages")
   def list_packages():
       import pkg_resources
       packages = [
           {"name": pkg.key, "version": pkg.version}
           for pkg in pkg_resources.working_set
       ]
       return {"packages": packages}
   ```

4. Compare the list against your requirements to identify any missing dependencies.

## Troubleshooting

If you encounter issues with the deployment, follow these steps:

1. Check the Vercel deployment logs for error messages
2. Verify all required environment variables are set
3. Ensure the `vercel.build.sh` script is executable and includes all necessary dependencies
4. Run the serverless compatibility test locally to identify potential issues
5. Check for file system access attempts in your code that might fail in a read-only environment
6. Verify that the Dowse logger patch is being applied correctly

For persistent issues, you can enable debug logging by setting the `LOG_LEVEL` environment variable to `DEBUG` in your Vercel project settings.

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

## Testing Serverless Compatibility

Before deploying to Vercel, it's recommended to test your application for serverless compatibility locally. A test script has been provided to simulate a serverless environment:

```bash
python tests/test_serverless.py
```

This script:

1. Checks your environment for compatibility issues (Python version, architecture, dependencies)
2. Creates a read-only directory to simulate Vercel's `/var/task` environment
3. Tests importing the Dowse logger to ensure it doesn't attempt to write to the filesystem
4. Tests importing the application with the patched logger
5. Verifies that the health endpoints work correctly
6. Checks for the presence of required dependencies like `pydantic_settings`

If the script runs successfully, your application should work properly in a serverless environment. If it fails, review the error messages and make the necessary adjustments before deploying.

### Using Poetry for Local Development

If you encounter architecture compatibility issues with dependencies like `pydantic_core`, it's recommended to use Poetry for local development:

```bash
# Install dependencies with Poetry
poetry install

# Run the serverless test with Poetry
poetry run python tests/test_serverless.py
```

This ensures that the correct architecture-specific packages are installed for your system.

## Troubleshooting

### Log Access

Access logs through the Vercel dashboard:

1. Go to your project
2. Click on the deployment
3. Navigate to "Functions" tab
4. Click on a function to view its logs

### Checking Installed Packages

To verify which packages are installed in your Vercel deployment, you can:

1. Check the build logs after deployment to view the contents of `installed_packages.txt` which is generated during the build process.

2. **Use the Debug Endpoint**: A debug endpoint has been added to easily check installed packages:

   ```
   GET /debug/packages
   ```

   This endpoint returns:

   - Current environment
   - Python version
   - Total package count
   - Complete list of installed packages with versions

   Note: This endpoint is disabled in production environments for security reasons.

3. Compare the list against your requirements to identify any missing dependencies.

### Common Error Codes

- **500**: Internal server error, check function logs
- **504**: Function execution timed out, consider increasing maxDuration
- **404**: Route or function not found, check routing configuration
- **403**: Forbidden, check authentication settings

### Common Serverless Errors

#### Missing Dependencies

If you encounter errors like:

```
ModuleNotFoundError: No module named 'pydantic_settings'
```

This indicates that a required Python package is missing from your deployment:

1. Add the missing package to your `requirements.txt` file
2. Explicitly install the package in your `vercel.build.sh` script
3. Check the "Required Dependencies" section above for common packages

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
