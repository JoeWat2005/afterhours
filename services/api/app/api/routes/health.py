from fastapi import APIRouter

from app.schemas.health import HealthResponse

# Create a router instance to group related endpoints
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    """
    Health check endpoint.

    Purpose:
    - Used to verify that the API service is running.
    - Typically called by load balancers, monitoring tools, or uptime checks.

    Returns:
    - A simple response indicating the service is up ("ok").
    """
    return HealthResponse(status="ok", service="afterhours-api")


@router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """
    Readiness check endpoint.

    Purpose:
    - Used to determine if the service is ready to handle requests.
    - Often used in container orchestration systems (e.g., Kubernetes)
      to decide when to route traffic to this service.

    Returns:
    - A response indicating the service is ready ("ready").
    """
    return HealthResponse(status="ready", service="afterhours-api")