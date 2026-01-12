# Production Deployment Guide

## Overview
This guide covers deploying the Snel backend to the Hetzner production server (snel-bot).

## Current Production Setup
- **Server**: snel-bot (Hetzner)
- **Location**: `/root/snel/backend`
- **Environment**: `.env` file with API keys and configuration
- **Process Manager**: PM2
- **Current Apps**: voisss-server, voisss-export-worker

## Changes in This Release
- Natural language payment command parsing
- Payment state persistence with transaction tracking
- Real ERC-20 transaction building and signing
- Wallet-based payment execution
- Transaction status monitoring from frontend
- x402 adapter and processor for Cronos integration
- Improved error handling and logging

## Pre-Deployment Checklist

### 1. Verify Local Changes Are Committed
```bash
cd /Users/udingethe/Dev/snel
git status  # Should be clean
git log --oneline -5  # Verify commits are pushed
```

### 2. Verify Production Environment
```bash
ssh snel-bot
cd ~/snel/backend
cat .env  # Verify all API keys are present
ls -la   # Check file structure
```

### 3. Review Backend Configuration
- Check `backend/app/config/settings.py` for production defaults
- Verify `backend/app/config/chains.py` has correct mainnet/testnet URLs
- Ensure API endpoints in `backend/app/main.py` are correct

### 4. Test Locally (Optional)
```bash
cd backend
bash start.sh --install-only
source .venv/bin/activate
python -m pytest tests/  # Run tests if available
```

## Deployment Steps

### Safe Deployment Method (Recommended)
```bash
cd /Users/udingethe/Dev/snel
./deploy.sh
```

This script will:
1. ✓ Create backup of current production .env and app/
2. ✓ Rsync code changes (excluding .env and venvs)
3. ✓ Install/update Python dependencies if needed
4. ✓ Restart the backend service
5. ✓ Show PM2 status

### Manual Deployment (If Preferred)

#### Step 1: SSH to Production
```bash
ssh snel-bot
cd ~/snel/backend
```

#### Step 2: Backup Current State
```bash
mkdir -p ~/snel_backups
cp .env ~/snel_backups/.env.$(date +%s)
cp -r app ~/snel_backups/app.$(date +%s)
```

#### Step 3: Pull Latest Changes
```bash
cd ~/snel
git pull origin main
cd backend
```

#### Step 4: Install Dependencies (if requirements.txt changed)
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

#### Step 5: Restart Service
```bash
# Using PM2 (if already configured)
pm2 restart snel-backend

# OR manually via start.sh
bash start.sh --use-9001
```

#### Step 6: Verify
```bash
pm2 status
curl http://localhost:9001/api/v1/health  # Or appropriate health endpoint
```

## Post-Deployment Verification

### 1. Check Service Status
```bash
ssh snel-bot "pm2 status"
ssh snel-bot "pm2 logs snel-backend --lines 50"
```

### 2. Test API Endpoints
```bash
# Health check
curl https://api.snel.io/api/v1/health

# Payment command parsing (example)
curl -X POST https://api.snel.io/api/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"command":"send 1 USDC to 0x1234..."}'

# Check transaction history
curl https://api.snel.io/api/v1/transactions
```

### 3. Frontend Integration Test
- Open https://stable-snel.netlify.app
- Test payment command submission
- Verify transaction status updates
- Check error handling

### 4. Monitor Logs
```bash
# Real-time logs
ssh snel-bot "pm2 logs snel-backend"

# Check for errors
ssh snel-bot "pm2 logs snel-backend --err"
```

## Troubleshooting

### Service Won't Start
```bash
ssh snel-bot
cd ~/snel/backend

# Check Python installation
python3 --version

# Manually test start
source .venv/bin/activate
python -c "import app; print('Imports OK')"

# Test with verbose output
uvicorn app.main:app --reload --port 9001
```

### Dependency Issues
```bash
ssh snel-bot
cd ~/snel/backend
source .venv/bin/activate

# Clear cache and reinstall
pip install --force-reinstall -r requirements.txt

# Check for version conflicts
pip check
```

### Environment Variables Missing
```bash
ssh snel-bot
cd ~/snel/backend

# Compare with example
diff .env .env.example

# Update .env if needed (preserve existing values)
# Then restart:
pm2 restart snel-backend
```

### Port Already in Use
```bash
ssh snel-bot

# Find process using port 9001
lsof -i :9001

# Kill if needed
kill -9 <PID>

# Or use different port
bash backend/start.sh --use-9002
```

## Rollback Procedure

If something goes wrong, rollback is simple:

```bash
ssh snel-bot
cd ~/snel/backend

# Get list of recent backups
ls -lt ~/snel_backups/ | head -10

# Restore from specific backup (replace TIMESTAMP)
cp ~/snel_backups/.env.TIMESTAMP .env
cp -r ~/snel_backups/app.TIMESTAMP/* app/

# Restart service
pm2 restart snel-backend
```

## Environment Variables Reference

### Required for Production
```
REDIS_URL=redis://localhost:6379
BRIAN_API_KEY=<api-key>
OPENAI_API_KEY=<api-key>
ZEROX_API_KEY=<api-key>
MNEE_API_KEY=<api-key>
ALLOWED_ORIGINS=https://stable-snel.netlify.app
```

### Optional
```
EXA_API_KEY=<for protocol discovery>
FIRECRAWL_API_KEY=<for protocol scraping>
AGNO_API_KEY=<for Agno integration>
```

## Monitoring and Maintenance

### Daily Health Checks
- Monitor PM2 status: `pm2 monit`
- Check error logs for exceptions
- Test API endpoints with curl
- Monitor server CPU/memory

### Weekly Tasks
- Review logs for patterns
- Check for any warnings in code
- Verify backups are being created
- Update dependencies if security patches available

### Monthly Tasks
- Full system backup
- Performance review
- Clean up old logs
- Test disaster recovery

## Performance Optimization Tips

1. **Redis**: Ensure Redis is running
   ```bash
   redis-cli ping  # Should return PONG
   ```

2. **Python**: Update to latest patch
   ```bash
   python3 -m pip install --upgrade pip
   ```

3. **Dependencies**: Keep updated
   ```bash
   pip list --outdated
   ```

4. **Memory**: Monitor with PM2
   ```bash
   pm2 monit
   ```

## Questions or Issues?

If deployment fails or behaves unexpectedly:
1. Check the deployment logs
2. Review git diff: `git diff HEAD~1 HEAD`
3. Check production .env vs .env.example
4. Test locally in `backend/` directory
5. Review this guide's troubleshooting section
