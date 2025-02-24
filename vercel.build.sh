#!/bin/bash

# Install Python packages from requirements.txt
pip install -r requirements.txt

# Install additional packages
pip install dowse emp-agents eth-rpc

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Ensure the script exits with success
exit 0 