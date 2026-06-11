from zone import Zone
from connection import Connection
from pydantic import BaseModel, model_validator


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: list[Connection]
    # start: Zone | None = None
    # goal: Zone | None = None
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {} #dict[origin.name, list[to.name]]

    @model_validator(mode='after')
    def make_adjencency(self) -> 'Graph':
        for conn in self.connections:
            self.adjacency.setdefault(conn.origin, []).append(conn.to)
            # self.adjacency.setdefault(conn.to, []).append(conn.origin)
        return self