"""
Patches for modules that are no longer used but still referenced.
This provides mock implementations to avoid import errors.
"""
import logging
import sys
import os

# Create a logger for dowse
dowse_logger = logging.getLogger("dowse")

# Configure dowse logger with reasonable defaults
def configure_dowse_logger():
    """Configure the dowse logger with reasonable defaults."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    dowse_logger.addHandler(handler)
    dowse_logger.setLevel(logging.INFO)
    dowse_logger.info("Dowse logger monkey patched for serverless environment")

# Create a module-like object to be imported as "dowse"
class DowseMock:
    """Mock implementation of the dowse module."""
    logger = dowse_logger
    
    # Add other attributes that might be accessed
    def __getattr__(self, name):
        # For any attributes we haven't explicitly defined, return a dummy object
        # that returns itself for any attribute access or method call
        return DummyObject(name)

class DummyObject:
    """A dummy object that returns itself for any attribute access or method call."""
    def __init__(self, name):
        self.name = name
    
    def __getattr__(self, name):
        return self
    
    def __call__(self, *args, **kwargs):
        return self

# Create a mock instance
dowse_mock = DowseMock()

def patch_modules():
    """Patch sys.modules with mock implementations."""
    # Only patch if the real module isn't already loaded
    if 'dowse' not in sys.modules:
        sys.modules['dowse'] = dowse_mock
    
    # Configure the logger
    configure_dowse_logger()

# Make the patch function available as a direct import
patch_dowse_modules = patch_modules

# Automatically apply the patches when this module is imported
patch_modules() 