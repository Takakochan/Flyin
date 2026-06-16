from zone import Zone, ZoneType
from connection import Connection
from pydantic import BaseModel, model_validator


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: dict[tuple[str, str], Connection]
    # start: Zone | None = None
    # goal: Zone | None = None
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {}
    """dict[origin.name, list[to.name]]"""

    @model_validator(mode='after')
    def make_adjencency(self) -> 'Graph':
        for conn in self.connections.values():
            self.adjacency.setdefault(conn.origin, []).append(conn.to)
            # self.adjacency.setdefault(conn.to, []).append(conn.origin)
        for key, zone in self.zones.items():
            if zone.zone_type == ZoneType.RESTRICTED:
                conn = next(c for (origin, to),
                            c in self.connections.items() if to == zone.name)
                conn.extra_step = True
        return self
