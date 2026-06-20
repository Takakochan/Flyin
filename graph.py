from zone import Zone, ZoneType
from connection import Connection
from pydantic import BaseModel, model_validator
from collections import defaultdict


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: dict[tuple[str, str], Connection]
    """
    connection =[origin, to], Connection
    """
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def make_adjencency(self) -> "Graph":
        self.adjacency = defaultdict(list)
        for conn in self.connections.values():
            self.adjacency[conn.origin].append(conn.to)
        for _, zone in self.zones.items():
            if zone.zone_type == ZoneType.RESTRICTED:
                conne = next(
                    c for (_, to), c in self.connections.items()
                    if to == zone.name
                )
                conne.extra_step = True
        return self
