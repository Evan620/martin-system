from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit, agents, dashboard, users

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
# Convert CORS_ORIGINS to list if it's a string
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["http://localhost:5173", "http://localhost:3000"],
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
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}")
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}")
app.include_router(users.router, prefix=f"{settings.API_V1_STR}")

@app.get("/")
async def root():
    return {"message": "Welcome to the ECOWAS Summit TWG Support System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
