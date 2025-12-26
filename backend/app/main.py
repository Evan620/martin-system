from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}")
app.include_router(twgs.router, prefix=f"{settings.API_V1_STR}")
app.include_router(meetings.router, prefix=f"{settings.API_V1_STR}")
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}")
app.include_router(action_items.router, prefix=f"{settings.API_V1_STR}")
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}")
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}")

@app.get("/")
async def root():
    return {"message": "Welcome to the ECOWAS Summit TWG Support System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
