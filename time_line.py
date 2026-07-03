from dataclasses import dataclass
from typing import Literal


@dataclass
class DroneState:
    """A single drone's position at one point in time.

    Attributes:
        id: Identifier of the drone.
        location: Zone name, or ``origin-to`` connection name, the drone is at.
        status: Whether the drone is in a zone,
        on a connection, or at the goal.
    """

    id: int
    location: str
    status: Literal["zone", "connection", "goal"]


@dataclass
class MoveEvent:
    """A drone moving to a destination on a given turn.

    Attributes:
        drone: Identifier of the drone that moves.
        to: Destination as a zone name or ``origin-to`` connection name.
    """

    drone: int
    to: str  # zone|connection


class TimeLine:
    """Ordered record of drone movements, one entry per turn.

    Attributes:
        turns: Move events per time step, indexed by turn number.
    """

    def __init__(self) -> None:
        """Initialize an empty timeline."""
        self.turns: list[list[MoveEvent]] = []

    def add_turn(self, events: list[MoveEvent]) -> None:
        """Append one turn's move events to the timeline.

        Args:
            events: The move events occurring on this turn.
        """
        self.turns.append(events)

    def get_state(self, t: int, drone_id: int) -> DroneState:
        """Resolve a drone's state at a given turn.

        The status is inferred from the location: a ``-`` in the name marks a
        connection, otherwise a zone.

        Args:
            t: Turn index to look up.
            drone_id: Identifier of the drone to find.

        Returns:
            The :class:`DroneState` for the drone at turn ``t``.

        Raises:
            KeyError: If the drone has no event recorded at turn ``t``.
        """
        for event in self.turns[t]:
            if drone_id == event.drone:
                return DroneState(
                    id=event.drone,
                    location=event.to,
                    status="connection" if "-" in event.to else "zone",
                )
        raise KeyError(f"drone {drone_id} not found as t = {t}")
