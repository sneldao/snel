#!/usr/bin/env python3
"""
Test script to verify Vercel serverless compatibility.
Run this script to check if your application is ready for Vercel deployment.
"""

import os
import sys
import logging
import importlib
import tempfile
import builtins
from pathlib import Path
import traceback

# Script configuration
TEST_MODULE_IMPORTS = [
    "src.dowse.logger",              # Check if Dowse logger is properly patched
    "app.utils.configure_logging",   # Check logging configuration
    "app.main",                      # Check app creation
    "api.index",                     # Check API entry point
    "api.middleware"                 # Check middleware
]

TEMP_FILE_CHECKS = [
    "/var/task/info.log",            # Common problem path
    "./info.log",                    # Another common path
    "dowse_info.log"                 # Dowse logger path
]

def simulate_vercel_environment():
    """Simulate Vercel environment variables."""
    os.environ["VERCEL"] = "1"
    os.environ["PYTHONPATH"] = "."
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["ENABLE_FILE_LOGGING"] = "false"
    # Make /var/task read-only in simulation
    global original_open
    original_open = builtins.open
    
    def mock_open(file, *args, **kwargs):
        # Simulate read-only file system for specific paths
        file_str = str(file)
        if any(file_str.startswith(prefix) for prefix in ["/var/task/", "/var/task"]):
            if args and (
                "w" in args[0] or 
                "a" in args[0] or 
                "+" in args[0]
            ):
                raise OSError(30, "Read-only file system", file_str)
        return original_open(file, *args, **kwargs)
    
    # Mock the built-in open function
    builtins.open = mock_open

def restore_environment():
    """Restore the original environment."""
    # Restore original open function
    if "original_open" in globals():
        builtins.open = original_open

def run_import_tests():
    """Test importing key modules with Vercel environment simulation."""
    results = {}
    
    for module_name in TEST_MODULE_IMPORTS:
        try:
            module = importlib.import_module(module_name)
            results[module_name] = {"status": "SUCCESS", "module": module}
        except Exception as e:
            results[module_name] = {
                "status": "FAILED", 
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    return results

def run_file_access_tests():
    """Test file access patterns that might fail in Vercel."""
    results = {}
    
    for file_path in TEMP_FILE_CHECKS:
        try:
            # Try to write to the file
            with open(file_path, "a+") as f:
                f.write("Test")
            results[file_path] = {"status": "ACCESSIBLE", "warning": "This might fail in Vercel"}
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            if "Read-only file system" in str(e):
                results[file_path] = {"status": "PROPERLY BLOCKED", "error": str(e)}
            else:
                results[file_path] = {"status": "OTHER ERROR", "error": str(e)}
        except Exception as e:
            results[file_path] = {
                "status": "UNEXPECTED ERROR", 
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    return results

def run_tmp_directory_test():
    """Test if /tmp directory is writable."""
    try:
        with tempfile.NamedTemporaryFile(dir="/tmp", prefix="vercel_test_", delete=False) as f:
            f.write(b"Test content")
            tmp_file = f.name
        
        # Read back the content
        with open(tmp_file, "r") as f:
            content = f.read()
        
        # Clean up
        os.remove(tmp_file)
        
        return {
            "status": "SUCCESS",
            "file": tmp_file,
            "content": content
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def main():
    """Run all Vercel compatibility tests."""
    print("=" * 80)
    print("VERCEL COMPATIBILITY TEST")
    print("=" * 80)
    
    # Set up test environment
    print("\nSetting up simulated Vercel environment...")
    simulate_vercel_environment()
    
    try:
        # Test imports
        print("\nTesting module imports:")
        import_results = run_import_tests()
        for module, result in import_results.items():
            status = result["status"]
            status_color = "\033[92m" if status == "SUCCESS" else "\033[91m"  # Green or Red
            print(f"  - {module}: {status_color}{status}\033[0m")
            if status != "SUCCESS":
                print(f"    Error: {result['error']}")
                # Uncomment to see full traceback
                # print(f"    Traceback: {result['traceback']}")
        
        # Test file access
        print("\nTesting file access patterns:")
        file_results = run_file_access_tests()
        for file_path, result in file_results.items():
            status = result["status"]
            if status == "PROPERLY BLOCKED":
                status_color = "\033[92m"  # Green
            elif status == "ACCESSIBLE":
                status_color = "\033[93m"  # Yellow
            else:
                status_color = "\033[91m"  # Red
            
            print(f"  - {file_path}: {status_color}{status}\033[0m")
            if "warning" in result:
                print(f"    Warning: {result['warning']}")
            if "error" in result:
                print(f"    Error: {result['error']}")
        
        # Test tmp directory
        print("\nTesting /tmp directory access:")
        tmp_result = run_tmp_directory_test()
        status_color = "\033[92m" if tmp_result["status"] == "SUCCESS" else "\033[91m"
        print(f"  - /tmp write access: {status_color}{tmp_result['status']}\033[0m")
        if tmp_result["status"] != "SUCCESS":
            print(f"    Error: {tmp_result['error']}")
        
        # Final assessment
        print("\n" + "=" * 80)
        success_imports = sum(1 for r in import_results.values() if r["status"] == "SUCCESS")
        proper_blocks = sum(1 for r in file_results.values() if r["status"] == "PROPERLY BLOCKED")
        tmp_success = tmp_result["status"] == "SUCCESS"
        
        if (success_imports == len(import_results) and 
            proper_blocks == len(file_results) and
            tmp_success):
            print("\033[92mVERCEL COMPATIBILITY TEST PASSED!\033[0m")
            print("Your application appears ready for Vercel deployment.")
            exit_code = 0
        else:
            print("\033[93mVERCEL COMPATIBILITY TEST PARTIAL SUCCESS\033[0m")
            print(f"Module imports: {success_imports}/{len(import_results)} successful")
            print(f"File access blocks: {proper_blocks}/{len(file_results)} properly blocked")
            print(f"Tmp directory: {'Accessible' if tmp_success else 'Not accessible'}")
            print("\nPlease review the warnings and errors above before deploying.")
            exit_code = 1
        
    finally:
        # Restore environment
        restore_environment()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 