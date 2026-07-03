from dataclasses import dataclass
from enum import StrEnum, Enum, auto
from typing import NamedTuple
from pydantic import BaseModel, Field


class Position(NamedTuple):
    """A 2D grid coordinate.

    Attributes:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """

    x: int
    y: int


class PositionValueError(Exception):
    """Raised when a position value has an invalid format.

    Attributes:
        value: The offending position value.
        message: Human-readable description of the problem.
    """

    def __init__(self, value: int, message: str) -> None:
        """Store the offending value and message.

        Args:
            value: The position value that failed validation.
            message: Human-readable description of the problem.
        """
        self.value = value
        self.message = message
        super().__init__(message)


@dataclass
class ZoneTypeNotExistError(ValueError):
    """Raised when a zone type string is not a valid :class:`ZoneType`.

    Attributes:
        line_num: 1-based line number where the invalid type appeared.
        value: The offending zone type string.
    """

    line_num: int
    value: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num} invalid zone_type {self.value} "
            f"valid Type are ['restricted', 'priority']"
        )


class ZoneType(StrEnum):
    """Movement semantics of a zone.

    Members prefixed with ``_`` are internal: ``_NORMAL`` is the default and
    ``_BLOCKED`` marks zones drones may not enter. ``RESTRICTED`` and
    ``PRIORITY`` are the user-specifiable types.
    """

    NORMAL = auto()
    BLOCKED = auto()
    RESTRICTED = auto()
    PRIORITY = auto()


class ZoneRole(StrEnum):
    """Role of a zone within the route: start, intermediate hub, or end."""

    START = auto()
    HUB = auto()
    END = auto()


class Zone(BaseModel):
    """A node in the map graph.

    Attributes:
        zone_role: Role within the route. Defaults to :attr:`ZoneRole.HUB`.
        name: Unique zone name.
        position: Grid coordinate of the zone.
        zone_type: Movement semantics. Defaults to ``_NORMAL``.
        color: Optional display color name.
        max_drones: Maximum drones allowed at once. Defaults to 1, minimum 0.
    """

    zone_role: ZoneRole = ZoneRole.HUB
    name: str
    position: Position
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, ge=0)


class ZoneState(Enum):
    """Runtime occupancy state of a zone."""

    AVAILABLE = auto()
    OCCUPIED = auto()


def validate_zone(info: str, line_num: int) -> str:
    """Validate a zone type string against :class:`ZoneType`.

    Args:
        info: The raw zone type string to validate.
        line_num: 1-based line number for error reporting.

    Returns:
        The matching :class:`ZoneType` value.

    Raises:
        ZoneTypeNotExistError: If the string is not a valid zone type.
    """
    try:
        zone = ZoneType(info)
    except ValueError:
        raise ZoneTypeNotExistError(line_num, info)
    return zone
