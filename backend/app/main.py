import faulthandler
faulthandler.enable()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit, agents, dashboard, users, notifications, supervisor, debug, pipeline, conflicts, settings as settings_router, shared_documents

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
# Convert CORS_ORIGINS to list if it's a string
# Convert CORS_ORIGINS to list if it's a string
# Handle CORS_ORIGINS which might be a string or a list
settings_cors = settings.CORS_ORIGINS
if isinstance(settings_cors, str):
    cors_origins = [origin.strip() for origin in settings_cors.split(",")]
else:
    cors_origins = list(settings_cors)

# Force add production origin to ensure it's never missed
if "https://frontend-production-1abb.up.railway.app" not in cors_origins:
    cors_origins.append("https://frontend-production-1abb.up.railway.app")

# Add custom domain
if "https://ecowasiisummit.net" not in cors_origins:
    cors_origins.append("https://ecowasiisummit.net")

if "https://www.ecowasiisummit.net" not in cors_origins:
    cors_origins.append("https://www.ecowasiisummit.net")

# Add TWG subdomain
if "https://twg.ecowasiisummit.net" not in cors_origins:
    cors_origins.append("https://twg.ecowasiisummit.net")

# Add IPv4 localhost variant to support 127.0.0.1 connections
if "http://127.0.0.1:5173" not in cors_origins:
    cors_origins.append("http://127.0.0.1:5173")

# Add localhost variant
if "http://localhost:5173" not in cors_origins:
    cors_origins.append("http://localhost:5173")

# Trust X-Forwarded-Proto headers from Railway/Load Balancers
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.on_event("startup")
async def startup_event():
    import logging
    import os
    from alembic.config import Config
    from alembic import command
    from app.core.google_utils import setup_google_credentials
    
    # Initialize Google Auth (restore credentials from env if needed)
    setup_google_credentials()
    
    logger = logging.getLogger("uvicorn.info")
    logger.info("--- STARTUP DIAGNOSTICS ---")
    
    # Run Database Migrations
    # TEMPORARILY DISABLED: asyncio event loop conflict
    # TODO: Run migrations manually with: alembic upgrade head
    logger.info("Skipping automatic migrations (run manually: alembic upgrade head)")

    
    logger.info(f"API_V1_STR: {settings.API_V1_STR}")
    logger.info(f"CORS_ORIGINS: {cors_origins}")
    logger.info(f"GOOGLE_CLIENT_ID Loaded: {bool(settings.GOOGLE_CLIENT_ID)}")
    if settings.GOOGLE_CLIENT_ID:
        logger.info(f"GOOGLE_CLIENT_ID Prefix: {settings.GOOGLE_CLIENT_ID[:10]}...")
    
    logger.info("REGISTERED ROUTES:")
    url_list = [{"path": route.path, "name": route.name} for route in app.routes]
    for route in url_list:
        logger.info(f"  {route['path']} ({route['name']})")

    # Start Scheduler
    from app.services.scheduler import scheduler_service
    scheduler_service.start()
    
    # Start Continuous Monitor (Background Conflict Detection)
    if not settings.DISABLE_IN_APP_MONITOR:
        from app.services.continuous_monitor import get_continuous_monitor
        monitor = get_continuous_monitor()
        monitor.start()
    else:
        logger.info("In-app ContinuousMonitor disabled (expecting Celery Beat to handle monitoring).")
    
    # Start Supervisor State Refresh Task
    from app.services.supervisor_state_service import get_supervisor_state
    from app.core.database import get_db_session_context

    async def refresh_supervisor_state_job():
        """Background task to refresh supervisor state"""
        logger.info("Executing background supervisor state refresh...")
        try:
            # Create a new session context
            async with get_db_session_context() as db:
                state_service = get_supervisor_state()
                await state_service.refresh_state(db)
                logger.info("Background supervisor state refresh completed.")
        except Exception as e:
            logger.error(f"Failed to refresh supervisor state: {e}")

    # Add the job to the scheduler (run every 5 minutes)
    # We need to access the scheduler instance from the service
    # Assuming scheduler_service exposes the underlying scheduler or has an add_job method
    # If not, we might need to modify scheduler_service. For now, let's assume standard APScheduler usage
    try:
        scheduler_service.scheduler.add_job(
            refresh_supervisor_state_job,
            'interval',
            minutes=5,
            id='supervisor_state_refresh',
            replace_existing=True
        )
        logger.info("Supervisor state refresh job added to scheduler.")
        
        # Execute immediate refresh to populate state on startup
        import asyncio
        asyncio.create_task(refresh_supervisor_state_job())
        logger.info("Triggered immediate supervisor state refresh.")
        
    except Exception as e:
        logger.error(f"Failed to add supervisor refresh job: {e}")

    # Add RSVP Sync Job (for Development/Standalone mode without Celery)
    from app.services.tasks import sync_rsvps
    try:
        scheduler_service.scheduler.add_job(
            sync_rsvps,
            'interval',
            minutes=1, # Run frequently for debugging
            id='sync_rsvps_job',
            replace_existing=True
        )
        logger.info("RSVP sync job added to scheduler (every 1 min).")
    except Exception as e:
        logger.error(f"Failed to add RSVP sync job: {e}")


    logger.info("--- END STARTUP DIAGNOSTICS ---")

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.scheduler import scheduler_service
    scheduler_service.shutdown()
    
    # Stop Continuous Monitor
    if not settings.DISABLE_IN_APP_MONITOR:
        from app.services.continuous_monitor import get_continuous_monitor
        get_continuous_monitor().stop()

# Register routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}")
app.include_router(twgs.router, prefix=f"{settings.API_V1_STR}")
app.include_router(meetings.router, prefix=f"{settings.API_V1_STR}")
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}")
app.include_router(action_items.router, prefix=f"{settings.API_V1_STR}")
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}")
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}")
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}")
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}")
app.include_router(users.router, prefix=f"{settings.API_V1_STR}")
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}")
app.include_router(supervisor.router, prefix=f"{settings.API_V1_STR}")
app.include_router(debug.router, prefix=f"{settings.API_V1_STR}")
app.include_router(pipeline.router, prefix=f"{settings.API_V1_STR}")
app.include_router(conflicts.router, prefix=f"{settings.API_V1_STR}")
app.include_router(settings_router.router, prefix=f"{settings.API_V1_STR}/settings", tags=["Settings"])
app.include_router(shared_documents.router, prefix=f"{settings.API_V1_STR}")
from app.api.routes import webhooks
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])

@app.get("/")
async def root():
    return {"message": "Welcome to the ECOWAS Summit TWG Support System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
