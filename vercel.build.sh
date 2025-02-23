#!/bin/bash

# Install Python packages
pip install -r requirements.txt

# Install dowse and its dependencies from PyPI
pip install dowse emp-agents eth-rpc

# Print installed packages for debugging
pip freeze 