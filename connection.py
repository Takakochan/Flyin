from pydantic import BaseModel, Field


class Connection(BaseModel):
    """A directed link between two zones in the map graph.

    Attributes:
        origin: Name of the zone the connection starts from.
        to: Name of the zone the connection leads to.
        max_link_capacity: Maximum number of drones allowed on the link at
            once. Defaults to 1 and must be at least 1.
        extra_step: Whether traversing this link costs an additional step.
            Defaults to False.
    """
    name: str
    origin: str
    to: str
    max_link_capacity: int = Field(default=1, ge=1)
    extra_step: bool = Field(default=False)
