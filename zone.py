from dataclasses import dataclass
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


@dataclass
class ZoneTypeNotExistError(ValueError):
    line_num: int
    value: str

    def __str__(self) -> str:
        return (f"Line {self.line_num} invalid zone_type {self.value} "
                f"valid Type are ['restricted', 'priority']")


class ZoneType(StrEnum):
    _NORMAL = auto()
    _BLOCKED = auto()
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
    zone_type: ZoneType = ZoneType._NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, ge=0)


class ZoneState(Enum):
    AVAILABLE = auto()
    OCCUPIED = auto()


def validate_zone(info: str, line_num: int) -> str:
    try:
        zone = ZoneType(info)
    except ValueError:
        raise ZoneTypeNotExistError(line_num, info)
    return zone
