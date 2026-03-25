from fastapi import APIRouter, Depends, Query

from app.api.deps.auth import AuthContext, get_auth_context
from app.schemas.heatmap import HeatmapResponse
from app.services.heatmap import HeatmapQuery, get_on_demand_heatmap


router = APIRouter()


@router.get("", response_model=HeatmapResponse)
async def get_heatmap(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_metres: int = Query(20000, gt=0, le=50000),
    cell_size_metres: int = Query(250, gt=0, le=2000),
    category: str = Query("all-crime", min_length=1, max_length=64),
    date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    auth: AuthContext = Depends(get_auth_context),
) -> HeatmapResponse:
    _ = auth
    result = await get_on_demand_heatmap(
        HeatmapQuery(
            latitude=latitude,
            longitude=longitude,
            radius_metres=radius_metres,
            cell_size_metres=cell_size_metres,
            category=category,
            date=date,
        )
    )

    return HeatmapResponse(
        latitude=result.latitude,
        longitude=result.longitude,
        radius_metres=result.radius_metres,
        cell_size_metres=result.cell_size_metres,
        category=result.category,
        date=result.date,
        items=result.items,
    )
