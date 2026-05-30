from zone import Zone
from connection import Connection
from pydantic import BaseModel


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: list[Connection]
    # start: Zone | None = None
    # goal: Zone | None = None
    nb_drone: int = 0

    # def add_zone(self, zone: Zone, line_nb: int) -> None:
    #     if zone.name is self.zones:
    #         raise ValueError(f"Line {line_nb} Dpplicated zone names {zone.name}")
    #     self.zones[zone.name] = zone

    # def add_connection(self, connection: Connection, line_nub: int) -> None: # <TO DO> think if I should make line_nb class
    #     if connection in self.connections: # <TO DO> How I should express dupplication of connection?? it should cover for both (a, b) != (b, a)
    #         raise ValueError(f"Line {line_num}: Dupplicated connection {connection}")