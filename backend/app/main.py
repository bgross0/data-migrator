from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import datasets, mappings, imports, health, sheets, addons, transforms, odoo, exports

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["health"])
app.include_router(datasets.router, prefix=settings.API_V1_PREFIX, tags=["datasets"])
app.include_router(sheets.router, prefix=settings.API_V1_PREFIX, tags=["sheets"])
app.include_router(mappings.router, prefix=settings.API_V1_PREFIX, tags=["mappings"])
app.include_router(addons.router, prefix=settings.API_V1_PREFIX, tags=["addons"])
app.include_router(transforms.router, prefix=settings.API_V1_PREFIX, tags=["transforms"])
app.include_router(odoo.router, prefix=settings.API_V1_PREFIX, tags=["odoo"])
app.include_router(imports.router, prefix=settings.API_V1_PREFIX, tags=["imports"])
app.include_router(exports.router, prefix=settings.API_V1_PREFIX, tags=["exports"])


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
