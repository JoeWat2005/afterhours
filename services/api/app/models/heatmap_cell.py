from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HeatmapCell(Base):
    """
    Database model representing a single cell in a spatial heatmap.

    Purpose:
    - Stores aggregated safety/risk data for a geographic area.
    - Each cell corresponds to a polygon region on the map.
    - Used for visualising risk levels (e.g., heatmaps in frontend maps).
    """

    __tablename__ = "heatmap_cells"

    # Unique identifier for the heatmap cell
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Polygon geometry representing the cell area (PostGIS)
    # - Geometry type: POLYGON
    # - SRID 4326: standard lat/lon coordinate system (WGS84)
    cell_geometry: Mapped[str] = mapped_column(
        Geometry("POLYGON", srid=4326),
        nullable=False,
    )

    # Risk score associated with this cell
    # - Typically computed from safety reports, incidents, or other data sources
    # - Higher values indicate higher risk
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Number of data sources contributing to this cell's score
    # - Helps indicate confidence or data density
    source_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Timestamp of the last update to this cell
    # - Useful for tracking freshness of heatmap data
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )