import json
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Query
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.heatmap_cell import HeatmapCell
from app.schemas.heatmap import HeatmapCellResponse, HeatmapIngestRequest, HeatmapResponse

# Create a router instance for heatmap-related endpoints
router = APIRouter()


@router.get("", response_model=HeatmapResponse)
async def list_heatmap(
    min_risk_score: float = Query(0, ge=0),
    limit: int = Query(200, gt=0, le=1000),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    """
    Retrieve a list of heatmap cells filtered by risk score.

    Purpose:
    - Returns heatmap data for visualisation (e.g., mapping risk levels).
    - Allows filtering by minimum risk score.
    - Limits the number of results returned for performance.

    Query Parameters:
    - min_risk_score:
        Minimum risk score threshold (default: 0).
        Only cells with risk_score >= this value are returned.
    - limit:
        Maximum number of records to return (default: 200, max: 1000).

    Dependencies:
    - db:
        Async database session injected via FastAPI dependency system.

    Returns:
    - HeatmapResponse containing a list of heatmap cells with geometry and metadata.
    """

    # Build SQL query:
    # - Select relevant fields from HeatmapCell
    # - Convert geometry column to GeoJSON using PostGIS ST_AsGeoJSON
    # - Filter by minimum risk score
    # - Order by highest risk first
    # - Limit number of results
    stmt = (
        select(
            HeatmapCell.id,
            HeatmapCell.risk_score,
            HeatmapCell.source_count,
            HeatmapCell.updated_at,
            func.ST_AsGeoJSON(HeatmapCell.cell_geometry).label("cell_geojson"),
        )
        .where(HeatmapCell.risk_score >= min_risk_score)
        .order_by(HeatmapCell.risk_score.desc())
        .limit(limit)
    )

    # Execute query asynchronously
    result = await db.execute(stmt)
    rows = result.all()

    # Transform database rows into response schema objects
    # - Parse GeoJSON string into Python dict
    items = [
        HeatmapCellResponse(
            id=row.id,
            risk_score=row.risk_score,
            source_count=row.source_count,
            updated_at=row.updated_at,
            cell_geojson=json.loads(row.cell_geojson),
        )
        for row in rows
    ]

    # Return structured API response
    return HeatmapResponse(items=items)


@router.post("/ingest", status_code=204)
async def ingest_heatmap_cells(
    payload: HeatmapIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Upsert a batch of scored heatmap cells produced by the worker's HeatmapEngine.

    Purpose:
    - Called by the aggregate_heatmaps worker job after scoring a grid.
    - Inserts new cells or updates existing ones based on geometry equality.
    - Skips cells with a risk_score of 0 to keep the table lean.

    Body:
    - cells: list of HeatmapCellInput objects (cell_geometry_wkt, risk_score, source_count)
    """
    now = datetime.now(UTC)

    rows = [
        {
            "cell_geometry": WKTElement(cell.cell_geometry_wkt, srid=4326),
            "risk_score": cell.risk_score,
            "source_count": cell.source_count,
            "updated_at": now,
        }
        for cell in payload.cells
        if cell.risk_score > 0  # skip empty cells to keep the table lean
    ]

    if not rows:
        return

    # PostgreSQL upsert: insert or update on geometry conflict
    stmt = pg_insert(HeatmapCell).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cell_geometry"],
        set_={
            "risk_score": stmt.excluded.risk_score,
            "source_count": stmt.excluded.source_count,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

