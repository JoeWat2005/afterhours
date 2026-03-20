from pydantic import BaseModel


class HealthResponse(BaseModel):
    """
    Schema representing the response for health and readiness endpoints.

    Purpose:
    - Provides a standard structure for service status checks.
    - Used by monitoring systems, load balancers, and orchestration tools.

    Fields:
    - status:
        Indicates the current state of the service (e.g., "ok", "ready").
    - service:
        Name of the service reporting the status.
    """

    # Current status of the service (e.g., "ok", "ready")
    status: str

    # Name/identifier of the service
    service: str