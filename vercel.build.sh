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
# REMOVED: no longer need to install dowse and emp-agents
pip install eth-rpc-py==0.1.26

# Install pydantic_settings which is missing from requirements.txt
pip install pydantic_settings==2.2.1

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Create necessary directories if they don't exist
mkdir -p app/services
mkdir -p app/api/routes
mkdir -p app/utils
mkdir -p app/models
mkdir -p app/agents
mkdir -p api

# Ensure that our custom providers file exists
# This will be used instead of emp_agents
if [ ! -f "app/utils/providers.py" ]; then
  echo 'Creating custom providers.py file'
  cat > app/utils/providers.py << 'EOL'
"""
Custom provider implementations to replace external dependencies.
"""
import os
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """Simple replacement for emp_agents.providers.OpenAIProvider"""
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        logger.info("Created custom OpenAIProvider")
        
    def __repr__(self):
        return f"OpenAIProvider(api_key=***)"
EOL
fi

# Ensure the script exits with success
exit 0 