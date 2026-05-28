# Railway Production Deployment Guide

## Quick Deploy (Automated)

```bash
# From project root
./deploy-to-railway.sh
```

The script will:
1. Install Railway CLI (if needed)
2. Authenticate you
3. Create/link project
4. Add Redis & PostgreSQL
5. Set environment variables
6. Deploy all services

## Manual Deployment Steps

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Login

```bash
railway login
```

### 3. Initialize Project

```bash
# Create new project
railway init

# Or link to existing
railway link
```

### 4. Add Databases

```bash
# Add Redis
railway add --database redis

# Add PostgreSQL (if not already added)
railway add --database postgresql
```

### 5. Set Environment Variables

```bash
# Copy from your .env file, or set manually:
railway variables set GITHUB_TOKEN="your-token"
railway variables set VEXA_API_KEY="your-key"
railway variables set RESEND_API_KEY="your-key"
railway variables set PINECONE_API_KEY="your-key"
railway variables set GOOGLE_CLIENT_ID="your-id"
railway variables set GOOGLE_CLIENT_SECRET="your-secret"
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set LLM_PROVIDER="github"
railway variables set LLM_MODEL="gpt-4o-mini"
```

### 6. Deploy Backend

```bash
cd backend
railway up
```

### 7. Create Additional Services

**In Railway Dashboard:**

1. **Create Worker Service**:
   - Click "New Service"
   - Select your backend repository
   - Set start command: `celery -A app.core.celery_app worker --loglevel=info --queues=monitoring,periodic,negotiations,formatting,scoring --concurrency=4`
   - Link same Redis & PostgreSQL databases
   - Copy all environment variables from backend service

2. **Create Beat Service**:
   - Click "New Service"
   - Select your backend repository
   - Set start command: `celery -A app.core.celery_app beat --loglevel=info`
   - Link same Redis & PostgreSQL databases
   - Copy all environment variables from backend service

3. **(Optional) Create Flower Service** (monitoring):
   - Click "New Service"
   - Select your backend repository
   - Set start command: `celery -A app.core.celery_app flower`
   - Link Redis database
   - Access at: `https://your-flower-service.railway.app`

## Verify Deployment

```bash
# Check backend health
curl https://your-backend.railway.app/health

# View logs
railway logs --service backend
railway logs --service worker
railway logs --service beat

# Check running tasks
railway run --service worker celery -A app.core.celery_app inspect active
```

## Scaling

### Add More Workers

In Railway Dashboard:
1. Go to Worker service
2. Click "Settings" → "Replicas"
3. Increase to 2-3 replicas

Or via CLI:
```bash
railway scale worker --replicas 3
```

### Resource Allocation (Recommended)

- **Backend**: 2GB RAM, 2 vCPU
- **Worker**: 1GB RAM per instance, 1 vCPU
- **Beat**: 512MB RAM, 0.5 vCPU
- **Redis**: 256MB (Railway managed)
- **PostgreSQL**: 1GB (Railway managed)

## Monitoring

### View Metrics
```bash
railway status
```

### Stream Logs
```bash
railway logs --service worker --follow
```

### Flower Dashboard (if deployed)
Visit: `https://your-flower-service.railway.app`

## Troubleshooting

### Worker Not Starting
```bash
# Check logs
railway logs --service worker

# Verify Redis connection
railway run --service worker python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"
```

### Tasks Not Running
```bash
# Check beat scheduler
railway logs --service beat

# Inspect scheduled tasks
railway run --service worker celery -A app.core.celery_app inspect scheduled
```

### Database Migration
```bash
# Run migrations
railway run --service backend alembic upgrade head
```

## Database migrations — operating rule

Schema changes go through **Alembic only**. No more `metadata.create_all` or
hand-rolled `ALTER TABLE` hotfixes on prod — they bypass version tracking and
cause the deploy migration step to fail later with phantom-revision errors.

### How a schema change ships

1. Edit the SQLAlchemy model (`backend/app/models/models.py`).
2. Add a migration in `backend/alembic/versions/`. Prefer idempotent DDL
   (`ALTER TABLE … ADD COLUMN IF NOT EXISTS …`) so the same file is safe to
   re-run if a deploy partially applied it.
3. Test locally: `cd backend && alembic upgrade head` — must finish without
   error.
4. Commit migration + model change together.
5. Deploy. The Dockerfile `CMD` already runs `alembic upgrade head` before
   `uvicorn`, so the migration applies automatically.

### One-time repair: phantom alembic marker

If a DB's `alembic_version` row points at a revision id that no longer exists
in `alembic/versions/` (this happens when someone ran `alembic stamp` with a
typo, or when a DB was bootstrapped via `metadata.create_all`), every
subsequent `alembic upgrade head` will fail with:

> `Can't locate revision identified by '<phantom>'`

Fix once per affected DB with the bundled script:

```bash
# Prod (laptop with Railway CLI):
railway run -s backend bash backend/scripts/repair_alembic_state.sh

# Local:
cd backend && bash scripts/repair_alembic_state.sh
```

The script:
- Reads `SELECT version_num FROM alembic_version`.
- Compares it to the revision ids present in `alembic/versions/*.py`.
- If the marker is real → exits 0 (no-op).
- If the marker is phantom → runs `alembic stamp head --purge` so future
  upgrades chain cleanly. The DB schema itself is not modified by the stamp.

After repair, deploys resume normally.

## Cost Estimate (Railway Pro)

- Base Pro Plan: $20/month
- Backend service: ~$10/month
- Worker service (2 replicas): ~$15/month
- Beat service: ~$5/month
- Redis: Included
- PostgreSQL: Included

**Total: ~$50/month** for production-ready setup serving 500+ users

## Environment Variables Reference

**Auto-set by Railway:**
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `PORT` - Service port

**Required (you set):**
- `GITHUB_TOKEN` - For LLM API
- `VEXA_API_KEY` - Meeting bot
- `RESEND_API_KEY` - Email service
- `PINECONE_API_KEY` - Vector database
- `SECRET_KEY` - JWT signing
- `GOOGLE_CLIENT_ID` - OAuth (optional)
- `GOOGLE_CLIENT_SECRET` - OAuth (optional)
- `FRONTEND_URL` - Your frontend URL
- `LLM_PROVIDER` - "github"
- `LLM_MODEL` - "gpt-4o-mini"
