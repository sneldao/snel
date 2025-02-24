#!/bin/bash

# Install Python packages from requirements.txt
pip install -r requirements.txt

# Install additional packages with specific versions
pip install dowse==0.1.0 emp-agents==0.2.0.post1 eth-rpc==0.1.26

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Create necessary directories if they don't exist
mkdir -p app/services

# Ensure the script exits with success
exit 0 