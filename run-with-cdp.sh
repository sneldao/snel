#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    echo "Usage: ./run-with-cdp.sh <python-script.py>"
    exit 1
fi

# Activate the virtual environment
source cdp-venv/bin/activate

# Run the specified script with the virtual environment's Python
python "$@"

# Deactivate the virtual environment
deactivate
