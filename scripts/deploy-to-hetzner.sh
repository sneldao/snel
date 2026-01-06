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
rsync -avz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.pyd' \
  --exclude='.pytest_cache' \
  --exclude='.DS_Store' \
  --exclude='dump.rdb' \
  --exclude='*.log' \
  --exclude='.env' \
  --exclude='.env.example' \
  --exclude='.env.coral' \
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
  backend/ snel-bot:/opt/snel-backend/

echo -e "${GREEN}Files synced successfully${NC}"

# Update the backend service on Hetzner
echo -e "${GREEN}Updating backend service on Hetzner server...${NC}"

ssh snel-bot << 'EOF'
set -e

# Navigate to the backend directory
cd /opt/snel-backend

# Check if .venv exists, if not create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (first time setup)..."
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Using existing virtual environment..."
    source .venv/bin/activate
fi

# Check if .env exists (required for runtime)
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found! Required for runtime configuration."
    echo "Please ensure .env is properly configured on the server."
    exit 1
fi

echo "✅ Environment configured"

# Restart using pm2 (manages service lifecycle)
if command -v pm2 &> /dev/null; then
    echo "Restarting backend service with pm2..."
    pm2 restart snel-backend --wait-ready --listen-timeout 5000 --kill-timeout 10000
    
    # Verify the service is running
    sleep 3
    if pm2 list | grep -q "snel-backend.*online"; then
        echo "✅ Backend service restarted successfully via pm2"
        
        # Check if the service is responding
        sleep 2
        if curl -s http://localhost:9001/ > /dev/null 2>&1; then
            echo "✅ Backend service is responding correctly"
        else
            echo "⚠️  Backend service may have started but is not responding properly"
            echo "Checking pm2 logs..."
            pm2 logs snel-backend --lines 20
        fi
    else
        echo "❌ Failed to restart backend service with pm2"
        pm2 logs snel-backend --lines 50
        exit 1
    fi
else
    echo "⚠️  pm2 not found, attempting manual restart..."
    
    # Fallback: manual restart
    pkill -f "uvicorn app.main:app" || true
    sleep 2
    
    nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9001 > snel_backend.log 2>&1 &
    sleep 5
    
    if pgrep -f "uvicorn app.main:app" > /dev/null; then
        echo "✅ Backend service restarted successfully"
    else
        echo "❌ Failed to restart backend service"
        tail -20 snel_backend.log
        exit 1
    fi
fi

echo "Deployment completed successfully!"
EOF

echo -e "${GREEN}Deployment to Hetzner server completed successfully!${NC}"
echo -e "${YELLOW}Backend should now be accessible via API at https://api.snel.famile.xyz${NC}"