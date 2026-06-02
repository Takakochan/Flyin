from zone import Zone
from connection import Connection
from pydantic import BaseModel


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: list[Connection]
    # start: Zone | None = None
    # goal: Zone | None = None
    nb_drone: int = 0
