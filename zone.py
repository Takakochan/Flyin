from dataclasses import dataclass
from enum import StrEnum, Enum, auto
from typing import NamedTuple
from pydantic import BaseModel, Field

class Position(NamedTuple):
    x: int
    y: int


class ZoneType(StrEnum):
    NORMAL = auto()
    BLOCKED = auto()
    RESTRICTED = auto()
    PRIORITY = auto()


class Zone(BaseModel):
    name: str
    position: Position
    max_drones: int = Field(default=1, ge=1)
    zone_type: ZoneType.NORMAL
    color: str | None = None



class ZoneState(Enum):
    AVAILABLE = auto()
    OCCUPIED = auto()


