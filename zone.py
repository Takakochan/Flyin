from enum import StrEnum, Enum, auto
from typing import NamedTuple
from pydantic import BaseModel, Field


class Position(NamedTuple):
    x: int
    y: int


class PositionValueError(Exception):
    """position values don't have right format"""

    def __init__(self, value: int, message: str) -> None:
        self.value = value
        self.message = message
        super().__init__(message)


class ZoneType(StrEnum):
    NORMAL = auto()
    BLOCKED = auto()
    RESTRICTED = auto()
    PRIORITY = auto()


class ZoneRole(StrEnum):
    START = auto()
    HUB = auto()
    END = auto()


class Zone(BaseModel):
    zone_role: ZoneRole = ZoneRole.HUB
    name: str
    position: Position
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, ge=1)


class ZoneState(Enum):
    AVAILABLE = auto()
    OCCUPIED = auto()
