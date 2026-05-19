from dataclasses import dataclass
from enum import StrEnum, Enum, auto
from typing import NamedTuple
from pydantic import BaseModel, field_validator


class Position(NamedTuple):
    """
    使うとき
    zone.position.x  # 名前でアクセスできる
    zone.position.y
    """
    x: int
    y: int

class ZoneType(StrEnum):
    NORMAL = auto()
    BLOCKED = auto()
    RESTRICTED = auto()
    PRIORITY = auto()

class Zone():
    name = str
    position = Position
	zone_type = ZoneType.NORMAL
    max_drone: int = 1
    color: str | None = None 

    @field_validator("max_drones")
    @classmethod
    def positive_num_drone(cls, v: int) -> int
        if v < 1:
            raise ValueError("Max_drone must be positive")
        return v

class ZoneState(Enum):
    AVAILABLE = auto()
    OCCUPIED = auto()



    