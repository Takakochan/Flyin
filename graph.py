from zone import Zone, ZoneType, ZoneRole
from connection import Connection
from pydantic import BaseModel, model_validator
from dataclasses import dataclass
from collections import defaultdict


class GraphValidationError(Exception):
    pass


@dataclass
class StartMissingError(GraphValidationError):
    detail: str

    def __str__(self) -> str:
        return f"{self.detail}"


@dataclass
class EndMissingError(GraphValidationError):
    detail: str

    def __str__(self) -> str:
        return f"{self.detail}"


class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: dict[tuple[str, str], Connection]
    """
    connection =[origin, to], Connection
    """
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {}
    """
    adjacency = name of origin, list[neighbour]
    """

    @model_validator(mode="after")
    def validator(self) -> "Graph":
        self.make_adjencency()
        self._validate_start_end()
        self._zero_drone_case()
        return self

    def make_adjencency(self) -> "Graph":
        self.adjacency = defaultdict(list)
        """
        defaultdict: It automatically assigns a default value to keys
        that do not exist which means no need to manually check
        for missing keys and avoid KeyError.
        """
        for conn in self.connections.values():
            self.adjacency[conn.origin].append(conn.to)
            self.adjacency[conn.to].append(conn.origin)
            """stupid but for the pdf requirement"""
        for _, zone in self.zones.items():
            if zone.zone_type == ZoneType.RESTRICTED:
                conne = next(
                    (c for (_, to), c in self.connections.items()
                     if to == zone.name),
                    None
                )
                if conne is not None:
                    conne.extra_step = True
        return self

    def _validate_start_end(self) -> None:
        if not any(
            zone.zone_role == ZoneRole.START for zone in self.zones.values()
        ):
            raise StartMissingError("Zone role 'start_hub' is missing")
        if not any(
            zone.zone_role == ZoneRole.END for zone in self.zones.values()
        ):
            raise EndMissingError("Zone role 'end_hub' is missing")

    def _zero_drone_case(self) -> None:
        for zone in self.zones.values():
            if zone.max_drones == 0:
                zone.zone_type = ZoneType._BLOCKED
