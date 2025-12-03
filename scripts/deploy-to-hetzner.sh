#!/bin/bash

# Script to deploy the SNEL backend to Hetzner server
# This script syncs the backend code to the Hetzner server and restarts the service

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment to Hetzner server...${NC}"

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory.${NC}"
    echo -e "${RED}Current directory: $(pwd)${NC}"
    exit 1
fi

# Sync only the backend directory, excluding unnecessary files
echo -e "${GREEN}Syncing backend files to Hetzner server...${NC}"

# rsync command that excludes development files but preserves runtime configurations
rsync -avz --delete \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.pyd' \
  --exclude='.pytest_cache' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='*.log' \
  --exclude='.env.local' \
  --exclude='.env.development' \
  --exclude='.env.production' \
  --exclude='.env.test' \
  --exclude='.gitignore' \
  --exclude='Dockerfile*' \
  --exclude='docker-compose*' \
  --exclude='README.md' \
  --exclude='Makefile' \
  --exclude='scripts/*' \
  --exclude='tests/*' \
  --exclude='test_*' \
  --exclude='.*' \
  backend/ snel-bot:/opt/snel-backend/

echo -e "${GREEN}Files synced successfully${NC}"

# Update the backend service on Hetzner
echo -e "${GREEN}Updating backend service on Hetzner server...${NC}"

ssh snel-bot << 'EOF'
set -e

# Navigate to the backend directory
cd /opt/snel-backend

# Backup existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Backing up existing virtual environment..."
    mv .venv .venv.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create new virtual environment
echo "Creating new virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install any additional dependencies that might be missing
pip install uvicorn fastapi python-dotenv redis

# Kill the existing backend process gracefully
echo "Shutting down existing backend service..."
sudo pkill -f "uvicorn app.main:app" || true
sleep 2

# Restart the backend service
echo "Starting the backend service..."
nohup ./start.sh > snel_backend.log 2>&1 &

# Verify the service is running
sleep 5
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "✅ Backend service restarted successfully"
    
    # Check if the service is responding
    if curl -s http://localhost:9001/api/v1/health/ > /dev/null; then
        echo "✅ Backend service is responding correctly"
    else
        echo "⚠️  Backend service may have started but is not responding properly"
    fi
else
    echo "❌ Failed to restart backend service"
    exit 1
fi

echo "Deployment completed successfully!"
EOF

echo -e "${GREEN}Deployment to Hetzner server completed successfully!${NC}"
echo -e "${YELLOW}Backend should now be accessible via API at https://api.snel.famile.xyz${NC}"