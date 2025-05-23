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

# Install dependencies if needed
echo -e "${BLUE}Installing dependencies...${NC}"

# Install python-dotenv first (the one that's causing the error)
pip install python-dotenv

# Install other core dependencies
echo -e "${BLUE}Installing core dependencies...${NC}"
pip install fastapi uvicorn httpx pydantic redis python-jose passlib bcrypt openai aiohttp

# Try to install the rest, but don't fail if some can't be installed
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

# Start the server
echo -e "${GREEN}Starting the server...${NC}"
uvicorn app.main:app --reload --port 8000

# This line won't be reached during normal operation since uvicorn will keep running
# But it's here for completeness
deactivate
