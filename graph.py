from zone import Zone, ZoneType
from connection import Connection
from pydantic import BaseModel, model_validator
<<<<<<< HEAD
from collections import defaultdict
=======
>>>>>>> 3b2c00bf9770a154cca12ac03b61bfc062d3107c


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: dict[tuple[str, str], Connection]
<<<<<<< HEAD
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
=======
    # start: Zone | None = None
    # goal: Zone | None = None
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {}
    """dict[origin.name, list[to.name]]"""

    @model_validator(mode="after")
    def make_adjencency(self) -> "Graph":
        for conn in self.connections.values():
            self.adjacency.setdefault(conn.origin, []).append(conn.to)
            # self.adjacency.setdefault(conn.to, []).append(conn.origin)
        for key, zone in self.zones.items():
            if zone.zone_type == ZoneType.RESTRICTED:
                conn = next(
                    c for (origin, to), c in self.connections.items() if to == zone.name
                )
                conn.extra_step = True
>>>>>>> 3b2c00bf9770a154cca12ac03b61bfc062d3107c
        return self
