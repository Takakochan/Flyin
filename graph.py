from zone import Zone, ZoneType, ZoneRole
from connection import Connection
from pydantic import BaseModel, model_validator
from dataclasses import dataclass
from collections import defaultdict


class GraphValidationError(Exception):
    """Base class for errors raised while validating a graph."""

    pass


@dataclass
class StartMissingError(GraphValidationError):
    """Raised when the graph has no start zone.

    Attributes:
        detail: Human-readable description of the problem.
    """

    detail: str

    def __str__(self) -> str:
        return f"{self.detail}"


@dataclass
class EndMissingError(GraphValidationError):
    """Raised when the graph has no end zone.

    Attributes:
        detail: Human-readable description of the problem.
    """

    detail: str

    def __str__(self) -> str:
        return f"{self.detail}"


class Graph(BaseModel):
    """The map as zones, connections and a derived adjacency list.

    The adjacency list is built and the graph validated automatically after
    construction by :meth:`validator`.

    Attributes:
        zones: Zones keyed by name.
        connections: Connections keyed by their ``(origin, to)`` pair.
        nb_drone: Number of drones to route. Defaults to 0.
        adjacency: Undirected neighbour list per zone name, populated by
            :meth:`make_adjencency`.
    """

    zones: dict[str, Zone]
    connections: dict[str, Connection]
    nb_drone: int = 0
    adjacency: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def validator(self) -> "Graph":
        """Build adjacency and validate the graph after construction.

        Runs as a Pydantic ``after`` validator: builds the adjacency list,
        checks that start and end zones exist, and blocks zero-capacity zones.

        Returns:
            The validated graph instance.

        Raises:
            StartMissingError: If no start zone is present.
            EndMissingError: If no end zone is present.
        """
        self.make_adjencency()
        self._validate_start_end()
        self._zero_drone_case()
        return self

    def make_adjencency(self) -> "Graph":
        """Build the undirected adjacency list from connections.

        Each connection contributes both directions. Restricted zones get their
        incoming connection flagged with ``extra_step`` so traversal into them
        costs an additional step.

        Returns:
            The graph instance, with :attr:`adjacency` populated.
        """
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
                    (c for c in self.connections.values() if c.to == zone.name), None
                )
                if conne is not None:
                    conne.extra_step = True
        return self

    def _validate_start_end(self) -> None:
        """Ensure exactly the required start and end zones exist.

        Raises:
            StartMissingError: If no zone has the start role.
            EndMissingError: If no zone has the end role.
        """
        if not any(zone.zone_role == ZoneRole.START for zone in self.zones.values()):
            raise StartMissingError("Zone role 'start_hub' is missing")
        if not any(zone.zone_role == ZoneRole.END for zone in self.zones.values()):
            raise EndMissingError("Zone role 'end_hub' is missing")

    def _zero_drone_case(self) -> None:
        """Block any zone whose capacity is zero.

        Zones with ``max_drones == 0`` are marked as blocked so no drone can
        route through them.
        """
        for zone in self.zones.values():
            if zone.max_drones == 0:
                zone.zone_type = ZoneType.BLOCKED
