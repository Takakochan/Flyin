from zone import Zone
from connection import Connection
from pydantic import BaseModel



class Graph(BaseModel):
    zones: dict[str, Zone] = {}
    connections: list[Connection] = []
    start: Zone | None = None
    goal: Zone | None = None
    nb_drone: int = 0

    def add_zone(self, zone: Zone) -> None:
        if zone.name is self.zones:
            raise ValueError(f"Dupplicated zone name {zone.name}")
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        if connection is self.connections:
            raise ValueError(f"Dupplicated connection {connection}")
