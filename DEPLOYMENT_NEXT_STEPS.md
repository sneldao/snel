# Next Steps for Production Deployment

## Summary of What's Done

✅ **All code changes staged, committed, and pushed**
- Production-ready payment system with wallet integration
- x402/Cronos adapter setup
- UI cleanup with "See Example" toggle
- 34 files changed, 2464 insertions

✅ **Deployment tools created**
- `deploy.sh` - Automated safe deployment script
- `backend/ecosystem.config.js` - PM2 configuration
- `DEPLOYMENT.md` - Comprehensive deployment guide

## When You're Ready to Deploy to Production

### Prerequisites
1. SSH access to snel-bot is working ✓
2. Backend directory exists at `/root/snel/backend` ✓
3. `.env` file with API keys exists on production ✓
4. Python virtual environment exists ✓

### Option A: Use Automated Deployment Script (Recommended)

```bash
# From workspace root
./deploy.sh
```

This single command will:
1. Backup production .env and app/ directory
2. Rsync all new code (preserving .env)
3. Install/upgrade Python dependencies if needed
4. Restart the backend service
5. Show you PM2 status

**Estimated time**: 2-3 minutes

### Option B: Manual Step-by-Step Deployment

```bash
# 1. SSH to production
ssh snel-bot

# 2. Go to backend directory
cd ~/snel/backend

# 3. Backup current state
mkdir -p ~/snel_backups
cp .env ~/snel_backups/.env.$(date +%s)
cp -r app ~/snel_backups/app.$(date +%s)

# 4. From your local machine, rsync code changes
# (From /Users/udingethe/Dev/snel on your Mac)
rsync -avz \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  backend/ \
  root@snel-bot:/root/snel/backend/

# 5. Back on production, restart
ssh snel-bot
cd ~/snel/backend
source .venv/bin/activate
pip install -r requirements.txt
pm2 restart snel-backend
```

## What Gets Deployed

### Backend Changes
- `app/config/` - Chain configuration for ERC-20 payments
- `app/domains/payment_actions/` - Payment processing service
- `app/core/parser/` - Natural language command parsing
- `app/models/` - Updated data models for transaction tracking
- `app/protocols/` - x402 adapter for Cronos
- `app/api/v1/` - New endpoints for payments and x402
- `app/services/` - Enhanced processors and knowledge base

### Frontend Will Continue Working
- No frontend deployment needed (already on Netlify)
- CORS is configured to `https://stable-snel.netlify.app`
- Backend will auto-serve the new endpoints

## Post-Deployment Health Checks

```bash
# Check service is running
ssh snel-bot "pm2 status"

# Check logs for errors
ssh snel-bot "pm2 logs snel-backend --lines 20"

# Test API
curl https://api.snel.io/api/v1/health

# Monitor in real-time
ssh snel-bot "pm2 monit"
```

## If Something Goes Wrong

### Instant Rollback (30 seconds)

```bash
ssh snel-bot
cd ~/snel/backend

# List recent backups
ls -lt ~/snel_backups/ | head -5

# Restore (use actual TIMESTAMP from above)
cp ~/snel_backups/.env.TIMESTAMP .env
cp -r ~/snel_backups/app.TIMESTAMP/* app/

# Restart
pm2 restart snel-backend
```

### Or Simply Pull Previous Git Commit
If code changes cause issues:
```bash
# From deployment server, in snel directory
cd /root/snel
git pull origin main
# ... or checkout specific commit if needed
```

## Important Notes

1. **API Keys Are Safe**
   - The deploy script explicitly excludes `.env` from rsync
   - Production .env is never overwritten
   - Backups are created before any changes

2. **No Downtime Required**
   - Rsync happens in background
   - Only brief pause during PM2 restart
   - Frontend continues working during deployment

3. **Monitoring**
   - PM2 will auto-restart if service crashes
   - Logs are stored at `/root/snel/backend/logs/`
   - Check Redis connectivity if payment features fail

4. **x402 Integration Note**
   - x402 adapter is in place but functionality is in-progress
   - Existing payment flows unaffected
   - Can be tested independently without affecting main system

## Configuration to Verify

Before deploying, verify these on production:

```bash
ssh snel-bot
cd ~/snel/backend

# 1. Check .env has all required keys
grep BRIAN_API_KEY .env
grep OPENAI_API_KEY .env
grep ZEROX_API_KEY .env
grep MNEE_API_KEY .env

# 2. Check Redis is accessible
redis-cli ping

# 3. Check Python version
python3 --version  # Should be 3.8+

# 4. Check existing processes
pm2 list
```

## Next Actions

**When ready to deploy:**

1. **Option A (Fast)**: Run `./deploy.sh` from workspace root
2. **Option B (Manual)**: Follow steps in DEPLOYMENT.md
3. **Monitor**: Use `ssh snel-bot "pm2 logs snel-backend"` to watch

**To keep working on x402:**
- x402 functionality can be developed further
- Your local dev environment has all the adapter code
- Deploy when ready without affecting other features

---

## Questions During Deployment?

Refer to:
- `DEPLOYMENT.md` - Detailed troubleshooting section
- Git history - `git log --oneline` shows all changes
- This file - Quick reference for procedures
