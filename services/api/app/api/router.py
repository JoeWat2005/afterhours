from fastapi import APIRouter

from app.api.routes import (
    health,
    routes,
    reports,
    journeys,
    heatmap,
    services,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(journeys.router, prefix="/journeys", tags=["journeys"])
api_router.include_router(heatmap.router, prefix="/heatmap", tags=["heatmap"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
