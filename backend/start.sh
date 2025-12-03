#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print script location for debugging
echo -e "${BLUE}Running script from: $(pwd)${NC}"

# Check for install-only mode
INSTALL_ONLY=false
if [ "$1" == "--install-only" ]; then
    INSTALL_ONLY=true
fi

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory.${NC}"
    echo -e "${RED}Current directory: $(pwd)${NC}"
    echo -e "${RED}Please change to the backend directory and try again.${NC}"
    exit 1
fi

# Check if virtual environment exists, create if it doesn't
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    # Try different Python commands
    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    elif command -v python &> /dev/null; then
        python -m venv .venv
    else
        echo -e "${RED}Python command not found. Please install Python 3.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
else
    echo -e "${BLUE}Using existing virtual environment.${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip first
echo -e "${BLUE}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install dependencies if needed
echo -e "${BLUE}Installing dependencies...${NC}"

# Install python-dotenv first
pip install python-dotenv

# Install core dependencies
echo -e "${BLUE}Installing core dependencies...${NC}"
pip install fastapi uvicorn httpx pydantic redis python-jose passlib bcrypt openai aiohttp

# Install web3 dependencies first
echo -e "${BLUE}Installing web3 dependencies...${NC}"
pip install "web3>=6.0.0" eth-utils eth-abi eth-account eth-typing

# Install and setup agno properly
echo -e "${BLUE}Setting up agno and its dependencies...${NC}"
pip uninstall -y agno || true  # Remove any existing installation
pip install -U agno --no-cache-dir

# Install Exa and Firecrawl for real data integration
echo -e "${BLUE}Installing Exa and Firecrawl for real data integration...${NC}"
pip install exa-py firecrawl-py

# Initialize agno
echo -e "${BLUE}Initializing agno...${NC}"
if ! command -v ag &> /dev/null; then
    echo -e "${YELLOW}Setting up agno CLI...${NC}"
    python -m agno.cli init || echo -e "${YELLOW}Agno CLI init skipped. You may need to run 'ag init' manually.${NC}"
fi

# Try to install the rest of the requirements
echo -e "${BLUE}Installing additional dependencies...${NC}"
pip install -r requirements.txt || echo -e "${YELLOW}Some dependencies could not be installed, but core functionality should work.${NC}"

# Check if .env file exists, create from example if it doesn't
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file from example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Created .env file. Please edit it with your API keys.${NC}"
fi

# Exit if in install-only mode
if [ "$INSTALL_ONLY" = true ]; then
    echo -e "${GREEN}Dependencies installed successfully.${NC}"
    deactivate
    exit 0
fi

# Allow port to be specified as command line argument, default to 8000 for backward compatibility
PORT=${2:-8000}
if [ "$1" == "--use-9001" ] || [ "$2" == "--use-9001" ]; then
    PORT=9001
fi

# Start the server
echo -e "${GREEN}Starting the server on port ${PORT}...${NC}"
uvicorn app.main:app --reload --port $PORT

# This line won't be reached during normal operation since uvicorn will keep running
# But it's here for completeness
deactivate
