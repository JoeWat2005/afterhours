from fastapi import APIRouter, Depends, Query

from app.api.deps.auth import get_current_app_user
from app.models.user import AppUser
from app.schemas.services import NearbyService, NearbyServicesResponse, ServiceCategory
from app.services.emergency_services import list_nearby_services

router = APIRouter()


@router.get("/nearby", response_model=NearbyServicesResponse)
async def nearby_services(
    latitude: float = Query(52.4862, ge=-90, le=90),
    longitude: float = Query(-1.8904, ge=-180, le=180),
    category: ServiceCategory | None = Query(default=None),
    radius_metres: int = Query(default=5000, gt=0, le=20_000),
    limit: int = Query(default=20, gt=0, le=100),
    current_user: AppUser = Depends(get_current_app_user),
) -> NearbyServicesResponse:
    _ = current_user
    items = list_nearby_services(
        latitude=latitude,
        longitude=longitude,
        category=category,
        radius_metres=radius_metres,
        limit=limit,
    )
    return NearbyServicesResponse(
        items=[NearbyService.model_validate(item) for item in items]
    )
