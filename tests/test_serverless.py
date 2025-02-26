#!/usr/bin/env python
"""
Test script to verify serverless compatibility.
This script simulates a serverless environment and tests the application's behavior.
"""

import os
import sys
import tempfile
import logging
import importlib
import platform
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("serverless_test")

def check_environment():
    """Check the current environment for compatibility issues."""
    logger.info("Checking environment compatibility...")
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    logger.info(f"Python version: {python_version}")
    
    # Check system architecture
    system = platform.system()
    machine = platform.machine()
    logger.info(f"System: {system}, Architecture: {machine}")
    
    # Check if Poetry is installed
    try:
        import subprocess
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Poetry installed: {result.stdout.strip()}")
        else:
            logger.warning("Poetry not found or not in PATH")
    except Exception as e:
        logger.warning(f"Error checking Poetry: {e}")
    
    # Check for pydantic_settings
    try:
        import pydantic_settings
        logger.info(f"pydantic_settings installed: {pydantic_settings.__version__}")
    except ImportError:
        logger.warning("pydantic_settings not installed")
    except Exception as e:
        logger.error(f"Error importing pydantic_settings: {e}")
    
    # Check for architecture-specific issues with pydantic_core
    try:
        import pydantic_core
        logger.info(f"pydantic_core installed: {pydantic_core.__version__}")
    except ImportError:
        logger.warning("pydantic_core not installed")
    except Exception as e:
        if "incompatible architecture" in str(e):
            logger.error(f"Architecture compatibility issue with pydantic_core: {e}")
            logger.error("Try reinstalling pydantic with Poetry: poetry install")
        else:
            logger.error(f"Error importing pydantic_core: {e}")

def test_read_only_filesystem():
    """Test application behavior with a read-only filesystem."""
    logger.info("Testing read-only filesystem compatibility...")
    
    # Set environment variables to simulate Vercel
    os.environ["VERCEL"] = "1"
    os.environ["ENVIRONMENT"] = "preview"
    os.environ["ENABLE_FILE_LOGGING"] = "false"
    
    # Create a temporary directory to simulate /var/task
    with tempfile.TemporaryDirectory() as temp_dir:
        var_task = Path(temp_dir) / "var" / "task"
        var_task.mkdir(parents=True, exist_ok=True)
        
        # Set current directory to the temporary directory
        original_cwd = os.getcwd()
        os.chdir(var_task)
        
        try:
            # Make the directory read-only
            os.chmod(var_task, 0o555)  # read and execute permissions only
            
            logger.info(f"Created read-only directory at {var_task}")
            
            # Add the original workspace to Python path
            sys.path.insert(0, original_cwd)
            
            # Test importing the dowse logger
            try:
                # First try to import the patched logger
                try:
                    from app.utils.dowse_logger_patch import patch_dowse_logger
                    patch_dowse_logger()
                    logger.info("Successfully patched dowse logger")
                except ImportError:
                    logger.warning("Logger patch not found, continuing without it")
                
                # Now try importing dowse.logger
                import dowse.logger
                logger.info("Successfully imported dowse.logger without errors")
            except Exception as e:
                logger.error(f"Error importing dowse.logger: {e}")
                logger.error(traceback.format_exc())
                return False
            
            # Test importing the app
            try:
                from app.main import app
                logger.info("Successfully imported app without errors")
            except Exception as e:
                logger.error(f"Error importing app: {e}")
                logger.error(traceback.format_exc())
                return False
            
            # Test creating a FastAPI test client
            try:
                from fastapi.testclient import TestClient
                client = TestClient(app)
                logger.info("Successfully created TestClient")
                
                # Test health endpoint
                response = client.get("/health")
                if response.status_code == 200:
                    logger.info(f"Health check successful: {response.json()}")
                else:
                    logger.error(f"Health check failed: {response.status_code} - {response.text}")
                    return False
                
                # Test debug packages endpoint
                response = client.get("/debug/packages")
                if response.status_code == 200:
                    packages = response.json()
                    logger.info(f"Found {packages.get('package_count', 0)} packages")
                    
                    # Check for pydantic_settings
                    package_list = packages.get('packages', [])
                    has_pydantic_settings = any("pydantic_settings" in pkg.lower() for pkg in package_list)
                    if has_pydantic_settings:
                        logger.info("pydantic_settings is installed")
                    else:
                        logger.warning("pydantic_settings not found in installed packages list, but may still be available")
                        # Check if we can import it directly
                        try:
                            import pydantic_settings
                            logger.info(f"pydantic_settings is available: {pydantic_settings.__version__}")
                        except ImportError:
                            logger.warning("pydantic_settings is not installed")
                else:
                    logger.error(f"Debug packages check failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error testing endpoints: {e}")
                logger.error(traceback.format_exc())
                return False
            
            logger.info("All serverless compatibility tests passed!")
            return True
            
        finally:
            # Restore original directory and permissions
            os.chmod(var_task, 0o755)  # restore write permissions
            os.chdir(original_cwd)
            
            # Clean up environment variables
            os.environ.pop("VERCEL", None)
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("ENABLE_FILE_LOGGING", None)

if __name__ == "__main__":
    # Check environment first
    check_environment()
    
    # Run the serverless test
    success = test_read_only_filesystem()
    sys.exit(0 if success else 1) 