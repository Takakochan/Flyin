from dataclasses import dataclass
from enum import StrEnum, Enum, auto
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from parser import Position


class ZoneRole(StrEnum):
    START = auto()
    HUB = auto()
    END = auto()


class ZoneType(StrEnum):
    NORMAL = auto()
    BLOCKED = auto()
    RESTRICTED = auto()
    PRIORITY = auto()


# <TODO> need to check if it's functions
class PositionValueError(Exception):
    """Position values don't have right format"""
    def __init__(self, value: int, message: str) -> None:
        self.value = value
        self.message = message
        super().__init__(message)


class Zone(BaseModel):
    """
    wondering if I can varidate most of the comming data with pydantic here. 
    """
    name: str
    position: Position
    max_drones: int = Field(default=1, ge=1)
    zone_type: ZoneType.NORMAL
    color: str | None = None


@field_validator('position')
@classmethod
def position_int(cls, value) -> Optional[int]:
    if value == int:
        raise PositionValueError(value,
                                 message="Position values shoud be integers")
    return value


class ZoneState(Enum):
    AVAILABLE = auto()
    OCCUPIED = auto()
