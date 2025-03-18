"""
Entry point for Vercel deployment.
This file is used by Vercel to run the application.
"""

import sys
import os
from pathlib import Path
import logging

# Setup paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_dir = os.path.dirname(os.path.abspath(__file__))

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# Import our patches module which will automatically apply the patches
from api.patches import patch_dowse_modules

# Apply the dowse logger patch
patch_dowse_modules()

# Now it's safe to import the app
from app.main import app 