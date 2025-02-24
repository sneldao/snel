from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
from typing import Optional, Dict, Any
import logging
import traceback
import json
from dotenv import load_dotenv
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_dir = os.path.dirname(os.path.abspath(__file__))

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# Load environment variables from all possible locations
env_files = [
    os.path.join(root_dir, '.env'),
    os.path.join(root_dir, '.env.local'),
    os.path.join(root_dir, '.env.production'),
]

for env_file in env_files:
    if os.path.exists(env_file):
        logger.info(f"Loading environment variables from {env_file}")
        load_dotenv(env_file)

# Log path information
logger.info(f"Root directory: {root_dir}")
logger.info(f"API directory: {api_dir}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current working directory: {os.getcwd()}")

# Create the ASGI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
api_init_error: Optional[Dict[str, Any]] = None
mounted_app: Optional[FastAPI] = None

def check_required_env_vars() -> Optional[Dict[str, Any]]:
    """Check if all required environment variables are present"""
    required_vars = [
        "OPENAI_API_KEY",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "QUICKNODE_ENDPOINT",
        "MORALIS_API_KEY",
        "COINGECKO_API_KEY",
        "ALCHEMY_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return {
            "error": f"Missing required environment variables: {', '.join(missing_vars)}",
            "trace": "Environment variables check failed",
            "type": "environment_error"
        }
    
    # Construct REDIS_URL from Upstash components if not present
    if not os.getenv("REDIS_URL"):
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if redis_url and redis_token:
            # Remove any trailing slashes
            redis_url = redis_url.rstrip("/")
            # Set the constructed URL
            os.environ["REDIS_URL"] = f"{redis_url}?token={redis_token}"
            logger.info("Constructed REDIS_URL from Upstash components")
    
    return None

# Initialize API
try:
    # Check environment variables first
    env_error = check_required_env_vars()
    if env_error:
        api_init_error = env_error
        raise Exception(env_error["error"])

    # Import your existing API functionality
    logger.info("Attempting to import api.py...")
    from api import app as api_app
    logger.info("Successfully imported api.py")
    
    # Store the mounted app
    mounted_app = api_app
    
    # Mount your existing API
    app.mount("/", api_app)
    logger.info("Successfully mounted API")

except Exception as e:
    error_trace = traceback.format_exc()
    api_init_error = {
        "error": str(e),
        "trace": error_trace,
        "type": "initialization_error"
    }
    logger.error(f"Failed to initialize API: {str(e)}\nTraceback:\n{error_trace}")

async def handle_api_request(request: Request, endpoint_name: str):
    """Generic handler for API requests that checks for initialization errors first"""
    if api_init_error:
        try:
            body = await request.json()
            logger.error(f"{endpoint_name} failed. Request body: {json.dumps(body)}")
        except Exception:
            body = "Could not parse request body"
            
        error_msg = {
            "detail": "API initialization failed",
            "error": api_init_error["error"],
            "trace": api_init_error["trace"],
            "request_body": body,
            "type": api_init_error["type"]
        }
        logger.error(f"{endpoint_name} failed: {error_msg}")
        return JSONResponse(status_code=500, content=error_msg)
    
    # If we get here, it means the API was initialized successfully
    # but we still need to handle the request properly
    try:
        if not mounted_app:
            raise Exception("API app not properly mounted")
            
        # Forward the request to the mounted app
        response = await mounted_app(request.scope, request.receive, request.send)
        return response
    except Exception as e:
        error_trace = traceback.format_exc()
        try:
            body = await request.json()
        except Exception:
            body = "Could not parse request body"
            
        error_msg = {
            "detail": "Request processing failed",
            "error": str(e),
            "trace": error_trace,
            "request_body": body,
            "type": "request_error"
        }
        logger.error(f"{endpoint_name} failed: {error_msg}")
        return JSONResponse(status_code=500, content=error_msg)

@app.post("/api/process-command")
async def process_command(request: Request):
    return await handle_api_request(request, "Command processing")

@app.post("/api/execute-transaction")
async def execute_transaction(request: Request):
    return await handle_api_request(request, "Transaction execution")

@app.get("/api/health")
async def health_check():
    env_vars = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "UPSTASH_REDIS_REST_URL": bool(os.getenv("UPSTASH_REDIS_REST_URL")),
        "UPSTASH_REDIS_REST_TOKEN": bool(os.getenv("UPSTASH_REDIS_REST_TOKEN")),
        "QUICKNODE_ENDPOINT": bool(os.getenv("QUICKNODE_ENDPOINT")),
        "MORALIS_API_KEY": bool(os.getenv("MORALIS_API_KEY")),
        "COINGECKO_API_KEY": bool(os.getenv("COINGECKO_API_KEY")),
        "ALCHEMY_KEY": bool(os.getenv("ALCHEMY_KEY"))
    }
    
    # Check Redis connection
    redis_status = {"status": "unknown"}
    try:
        if os.getenv("REDIS_URL"):
            from upstash_redis import Redis
            redis = Redis.from_env()
            await redis.ping()
            redis_status = {"status": "healthy"}
    except Exception as e:
        redis_status = {
            "status": "error",
            "error": str(e)
        }
    
    paths = {
        "root_dir": root_dir,
        "api_dir": api_dir,
        "cwd": os.getcwd(),
        "python_path": sys.path
    }
    
    if api_init_error:
        return {
            "status": "error",
            "message": api_init_error["error"],
            "trace": api_init_error["trace"],
            "type": api_init_error["type"],
            "paths": paths,
            "env_vars": env_vars,
            "services": {
                "redis": redis_status
            }
        }
    
    try:
        # Verify API is still working
        from api import app as api_app
        return {
            "status": "ok",
            "paths": paths,
            "env_vars": env_vars,
            "services": {
                "redis": redis_status
            },
            "mounted_app": bool(mounted_app)
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        return {
            "status": "error",
            "message": str(e),
            "trace": error_trace,
            "paths": paths,
            "env_vars": env_vars,
            "services": {
                "redis": redis_status
            },
            "mounted_app": bool(mounted_app)
        }

# Error handler for 500 errors
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    error_trace = traceback.format_exc()
    logger.error(f"Internal server error: {str(exc)}\nTraceback:\n{error_trace}")
    
    try:
        body = await request.json()
        logger.error(f"Request body: {json.dumps(body)}")
    except Exception:
        body = "Could not parse request body"
        
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc),
            "trace": error_trace,
            "request_body": body,
            "type": "runtime_error",
            "paths": {
                "root_dir": root_dir,
                "api_dir": api_dir,
                "cwd": os.getcwd()
            }
        }
    ) 