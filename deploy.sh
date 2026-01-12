#!/bin/bash

# Production Deployment Script
# This script safely deploys the backend to the Hetzner production server
# It preserves the production .env file and handles service restart

set -e

PROD_USER="root"
PROD_HOST="snel-bot"
PROD_PATH="/root/snel"
LOCAL_PATH="/Users/udingethe/Dev/snel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="/root/snel_backups"

echo "========================================="
echo "Snel Backend Deployment Script"
echo "Timestamp: $TIMESTAMP"
echo "========================================="

# Step 1: Create backup directory on production
echo ""
echo "[1/5] Creating backup directory on production..."
ssh "$PROD_USER@$PROD_HOST" "mkdir -p $BACKUP_PATH"

# Step 2: Backup current .env and app directory
echo "[2/5] Backing up production .env and app..."
ssh "$PROD_USER@$PROD_HOST" "cp $PROD_PATH/backend/.env $BACKUP_PATH/.env.$TIMESTAMP"
ssh "$PROD_USER@$PROD_HOST" "cp -r $PROD_PATH/backend/app $BACKUP_PATH/app.$TIMESTAMP"
echo "Backup saved to: $BACKUP_PATH/.env.$TIMESTAMP and $BACKUP_PATH/app.$TIMESTAMP"

# Step 3: Rsync code (excluding .env and sensitive files)
echo ""
echo "[3/5] Rsyncing code changes to production..."
echo "Syncing: $LOCAL_PATH/backend/ -> $PROD_USER@$PROD_HOST:$PROD_PATH/backend/"
rsync -avz \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='.git' \
  "$LOCAL_PATH/backend/" \
  "$PROD_USER@$PROD_HOST:$PROD_PATH/backend/"

echo "Code sync complete!"

# Step 4: Check if requirements have changed and reinstall if needed
echo ""
echo "[4/5] Checking and updating Python dependencies..."
ssh "$PROD_USER@$PROD_HOST" "cd $PROD_PATH/backend && \
  if ! diff -q requirements.txt .requirements_deployed 2>/dev/null; then \
    echo 'Requirements changed, installing dependencies...'; \
    source .venv/bin/activate && pip install -r requirements.txt --upgrade; \
    cp requirements.txt .requirements_deployed; \
    echo 'Dependencies installed'; \
  else \
    echo 'Requirements unchanged'; \
  fi"

# Step 5: Restart the backend service
echo ""
echo "[5/5] Restarting backend service..."
ssh "$PROD_USER@$PROD_HOST" "pm2 restart snel-backend 2>/dev/null || \
  (cd $PROD_PATH/backend && bash start.sh)"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Production URL: https://api.snel.io"
echo "PM2 Status:"
ssh "$PROD_USER@$PROD_HOST" "pm2 list"

echo ""
echo "Backup Info:"
echo "- .env backup: $BACKUP_PATH/.env.$TIMESTAMP"
echo "- app backup: $BACKUP_PATH/app.$TIMESTAMP"
echo ""
echo "To rollback if needed:"
echo "  ssh $PROD_USER@$PROD_HOST"
echo "  cp $BACKUP_PATH/.env.$TIMESTAMP $PROD_PATH/backend/.env"
echo "  cp -r $BACKUP_PATH/app.$TIMESTAMP/* $PROD_PATH/backend/app/"
echo "  pm2 restart snel-backend"
