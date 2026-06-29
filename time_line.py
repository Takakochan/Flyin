from dataclasses import dataclass
from typing import Literal


@dataclass
class DroneState:
    id: int
    location: str  # zone | connection
    status: Literal["zone", "connection", "goal"]


@dataclass
class MoveEvent:
    drone: int
    to: str  # zone | connection


class TimeLine:
    def __init__(self):
        self.turns: list[list[MoveEvent]] = []

    def add_turn(self, events: list[MoveEvent]) -> None:
        self.turns.append(events)

    def get_state(self, t: int, drone_id: int) -> DroneState:
        for event in self.turns[t]:
            if drone_id == event.drone:
                return DroneState(
                    id=event.drone,
                    location=event.to,
                    status="connection" if "-" in event.to else "zone")
        raise KeyError(f"drone {drone_id} not found as t={t}")
