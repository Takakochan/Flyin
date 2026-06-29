import glob
import inquirer
from collections.abc import Callable
from typing import Any
from functools import wraps
from dataclasses import dataclass
from enum import StrEnum, auto

from domain.color import validate_color
from graph import Graph
from zone import Zone, ZoneType, ZoneRole, Position, validate_zone
from connection import Connection

type ExportFn = Callable[[str, int, ParseState], ParseUpdate]
type SetterFn = Callable[[ConfigKeyWords, list[Any], int], Any]


class ConfigKeyWords(StrEnum):
    """Keywords used to tag and route parsed configuration fields.
    The values double as dictionary keys for the parsed data so that the same
    enum members identify both the kind of update an exporter produces and the
    field names stored inside it.
    """

    ZONE = auto()
    CONNECTION = auto()
    NAME = auto()
    ORIGIN = auto()
    TO = auto()
    NB_DRONE = auto()


EXPORTERS: dict[str, ExportFn] = {}
SETTERS: dict[ConfigKeyWords, SetterFn] = {}
SEPARATORS = (":", "[", "=")


@dataclass
class ParseState:
    """Mutable accumulator holding parsing progress for a single file.

    Attributes:
        zones: Parsed zone definitions, each stored as a keyword-to-value dict.
        zone_names: Names of zones already seen, used to detect duplicates.
        connections: Parsed connections keyed by their ``(origin, to)`` pair.
        connection_seen: Unordered zone pairs already connected, used to detect
                        duplicate connections regardless of direction.
        nb_drones: Number of drones declared by the ``nb_drones`` line.
    """
    zones: list[dict[str, Any]]
    zone_names: set[str]
    connections: dict[tuple[str, str], dict[str, Any]]
    connection_seen: set[frozenset[str]]
    nb_drones: int


@dataclass
class ParseUpdate:
    """A single unit of data produced by an exporter for one input line.

    Attributes:
        target: The :class:`ConfigKeyWords` category this update belongs to.
        data: Field values extracted from the line.
        line_num: 1-based line number the data was read from.
    """
    target: str
    data: dict[str, Any]
    line_num: int


class ParserError(Exception):
    """Base class for all errors raised while parsing a map file."""

    pass


@dataclass
class FormatError(ParserError):
    line_num: int | None
    detail: str

    def __str__(self) -> str:
        if self.line_num is None:
            return self.detail
        return f"Line {self.line_num}: {self.detail}"


@dataclass
class HubAttributeError(ParserError):
    line_num: int
    details: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.details} Expected atributes"
            "ex) [zone=restricted color=maroon max_drones=2]"
        )


@dataclass
class HubAttributeDuplicatesError(ParserError):
    line_num: int
    detail: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.detail}. "
            "Each attribue (zone, color, max_drones) should appear only once"
        )


@dataclass
class HubFormatError(ParserError):
    line_num: int
    detail: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.detail}, "
            "Expected 'hub: hub-name <int> <int> [zone=<optional> "
            "color=<optional> max_drones=<positive int>]'"
        )


@dataclass
class ConnectionFormatError(ParserError):
    line_num: int
    detail: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.detail} "
            "Expected 'connection: <name of hub>-<name of hub> "
            "[Optionl-<max_link_capacity=positive int>]'"
        )


@dataclass
class UnknownKeyError(ParserError):
    line_num: int
    keyword: str

    def __str__(self) -> str:
        return f"Line {self.line_num}: Unknown keyword '{self.keyword}"


@dataclass
class ValueRangeError(ParserError):
    line_num: int
    field: str
    detail: str

    def __str__(self) -> str:
        return f"Line {self.line_num}: [{self.field}] {self.detail}"


@dataclass
class DuplicatedConnectionError(ParserError):
    line_num: int
    fig: str
    detail: str

    def __str__(self) -> str:
        return f"Line {self.line_num}: [{self.fig}] {self.detail} "


@dataclass
class ZoneNameError(ParserError):
    line_num: int
    fig: str
    detail: str

    def __str__(self) -> str:
        return f"Line {self.line_num}: [{self.fig}] {self.detail} "


def register_exporter(key_word: str) -> Callable[[ExportFn], ExportFn]:
    """Create a decorator that registers an exporter under a keyword.

    Args:
        key_word: Leading keyword that maps to the decorated exporter in
            :data:`EXPORTERS`.

    Returns:
        A decorator that registers the function in :data:`EXPORTERS` and
        returns it unchanged.
    """
    def decorator(func: ExportFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        EXPORTERS[key_word] = wrapper
        return wrapper

    return decorator


def setter_machine(name: ConfigKeyWords) -> Callable[[SetterFn], ExportFn]:
    """Create a decorator that registers a setter under a config keyword.

    Args:
        name: The :class:`ConfigKeyWords` key the decorated setter is stored
            under in :data:`SETTERS`.

    Returns:
        A decorator that registers the function in :data:`SETTERS` and returns
        it unchanged.
    """
    def decorator(func: SetterFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        SETTERS[name] = wrapper
        return wrapper

    return decorator


def select_file() -> str:
    """Prompt the user to choose a map file from ``maps/``.

    Searches ``maps/**/*.txt`` and presents the matches in an interactive list.

    Returns:
        The path of the selected ``.txt`` map file.

    Raises:
        ValueError: If the prompt is cancelled and no file is selected.
    """
    dir_path = glob.glob("maps/**/*.txt")
    question = [
        inquirer.List(
            "Choose a file",
            message="which file would like to try?",
            choices=dir_path,
        )
    ]
    answers = inquirer.prompt(question)
    if not answers:
        raise ValueError("No file selected")
    selected: str = answers["Choose a file"]
    print(f"The file {selected} is selected")
    return selected


def parser(file_path: str) -> Graph:
    """Parse a map file into a :class:`Graph`.

    Reads the file line by line, skipping blank lines and ``#`` comments,
    dispatches each line to its exporter, and accumulates zones, connections
    and the drone count. Start and end zones inherit ``nb_drones`` as their
    ``max_drones`` before the graph is built.

    Args:
        file_path: Path to the map definition file.

    Returns:
        A :class:`Graph` built from the parsed zones, connections and drone
        count.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
        FormatError: If the required ``nb_drones`` declaration is missing.
        ParserError: For any other validation failure raised while parsing.
    """
    state = ParseState(
        zones=[],
        zone_names=set(),
        connections={},
        connection_seen=set(),
        nb_drones=0,
    )
    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("\n"):
                    continue

                fetched = export_data(line, line_num, state)
                match fetched.target:
                    case ConfigKeyWords.ZONE:
                        handle_zone(state, fetched, line_num)
                    case ConfigKeyWords.CONNECTION:
                        handle_connection(state, fetched, line_num)
                    case ConfigKeyWords.NB_DRONE:
                        state.nb_drones = fetched.data["nb_drones"]

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    if state.nb_drones is None:
        raise FormatError(None, "nb_drones is missing")
    for zone_data in state.zones:
        if zone_data.get("zone_role") in (ZoneRole.START, ZoneRole.END):
            zone_data["max_drones"] = state.nb_drones
    return Graph(
        zones={dat[ConfigKeyWords.NAME]: Zone(**dat) for dat in state.zones},
        connections={
            key: Connection(**cnc) for key, cnc in state.connections.items()
        },
        nb_drone=state.nb_drones,
    )


def handle_zone(
        state: ParseState,
        fetched: ParseUpdate,
        line_num: int
) -> None:
    """Record a parsed zone, rejecting duplicate names.

    Args:
        state: Parsing accumulator to update in place.
        fetched: Parsed zone data for the current line.
        line_num: 1-based line number for error reporting.

    Raises:
        ZoneNameError: If the zone name was already declared.
    """
    name = fetched.data[ConfigKeyWords.NAME]
    if name in state.zone_names:
        raise ZoneNameError(
            line_num, name, "is duplicated"
        )
    state.zone_names.add(name)
    state.zones.append(fetched.data)


def handle_connection(
        state: ParseState,
        fetched: ParseUpdate,
        line_num: int
) -> None:
    """Record a parsed connection, rejecting duplicate pairs.

    The duplicate check is direction-insensitive, so ``a-b`` and ``b-a`` are
    treated as the same connection.

    Args:
        state: Parsing accumulator to update in place.
        fetched: Parsed connection data for the current line.
        line_num: 1-based line number for error reporting.

    Raises:
        DuplicatedConnectionError: If the same zone pair was already connected.
    """
    pair = frozenset(
        {
            fetched.data[ConfigKeyWords.ORIGIN],
            fetched.data[ConfigKeyWords.TO],
        }
    )
    if pair in state.connection_seen:
        connection_name = f"{list(pair)[0]}-{list(pair)[1]}"
        raise DuplicatedConnectionError(
            line_num, connection_name, "Duplicated connection name"
        )
    state.connection_seen.add(pair)
    state.connections[
        (fetched.data[ConfigKeyWords.ORIGIN], fetched.data[ConfigKeyWords.TO])
    ] = fetched.data


def export_data(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    """Dispatch a line to its registered exporter by leading keyword.

    The keyword is taken as the text before the first separator found in
    :data:`SEPARATORS`.

    Args:
        line: Raw, stripped input line.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator, passed through to the exporter.

    Returns:
        The :class:`ParseUpdate` produced by the matching exporter.

    Raises:
        HubFormatError: If the line contains no known separator, or the
            extracted keyword has no registered exporter.
    """
    for sep in SEPARATORS:
        if sep in line:
            title, _, info = line.partition(sep)
            exporter = EXPORTERS.get(title)
            if exporter is None:
                raise HubFormatError(
                    line_num, "unexpected format"
                )
            return exporter(line, line_num, state)
    raise HubFormatError(line_num, "unexpected format")


@register_exporter("nb_drones")
def _get_nb_drones(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    """Parse a ``nb_drones: <n>`` line.

    Args:
        line: Raw input line.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator (unused).

    Returns:
        A :class:`ParseUpdate` carrying the drone count.

    Raises:
        FormatError: If the line does not have exactly two whitespace tokens.
        ValueRangeError: If the count is not a positive integer.
    """
    words = line.split()
    if len(words) != 2:
        raise FormatError(
            line_num,
            "the for mat is expected:: 'nb_drones: <positive number>'"
        )
    try:
        nb_drones = int(words[1])
    except ValueError:
        raise ValueRangeError(
            line_num, "nb_drones", "must be a positive integer"
        )

    if nb_drones <= 0:
        raise ValueRangeError(
            line_num, "nb_drones", "must be positive"
        )
    return ParseUpdate(
        target=ConfigKeyWords.NB_DRONE, data={"nb_drones": nb_drones},
        line_num=line_num
    )


@register_exporter("start_hub")
@register_exporter("end_hub")
@register_exporter("hub")
def _get_zone_info(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    """Parse a ``hub`` / ``start_hub`` / ``end_hub`` line into a zone.

    Splits the line into the positional part (role, name, x, y) and the
    bracketed attribute part, then merges the parsed attributes onto the zone
    data. The role is derived from the keyword's prefix (e.g. ``start_hub`` ->
    ``start``).

    Args:
        line: Raw input line.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator, forwarded to attribute parsing.

    Returns:
        A :class:`ParseUpdate` describing the zone (role, name, position and
        attributes).

    Raises:
        HubFormatError: If the attribute brackets are missing or the positional
            part does not have exactly four tokens.
        ValueRangeError: If the coordinates are not integers.
    """
    if "[" not in line and "]" not in line:
        raise HubFormatError(
            line_num, "Attribute is not given"
        )
    hub, _, attrb = line.partition("[")
    hubs = hub.split()
    if len(hubs) != 4:
        raise HubFormatError(line_num, "Wrong format")
    role = hubs[0].strip(":")
    role, _, _ = role.partition("_")
    name = hubs[1].strip()
    try:
        x = int(hubs[2])
        y = int(hubs[3])
    except ValueError:
        raise ValueRangeError(
            line_num, "nb_drones", "should be a positive integer"
        )
    attribute_dict = _get_attribute(attrb, line_num, state)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data=(
            {
                "zone_role": role,
                ConfigKeyWords.NAME: name,
                "position": Position(x=x, y=y),
            } | attribute_dict
        ),
        line_num=line_num,
    )


def _get_attribute(
        atrbt: str, line_num: int, state: ParseState
) -> dict[str, Any]:
    """Parse the bracketed attribute section of a hub line.

    Accepts up to three attributes (``zone``, ``color``, ``max_drones``), each
    at most once, and merges their parsed values into a single dict.

    Args:
        atrbt: Attribute text, optionally still wrapped in a trailing ``]``.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator; a fresh one is created if ``None``.

    Returns:
        A dict mapping attribute fields to their parsed values.

    Raises:
        HubAttributeError: If more than three attributes are given, or any
            single attribute appears more than once.
    """
    if state is None:
        state = ParseState(
            zones=[], zone_names=set(),
            connections={}, connection_seen=set(), nb_drones=0
        )
    attribute_dict: dict[str, Any] = {}
    a_zone = 0
    a_color = 0
    a_drone = 0
    atrbt = atrbt.strip("]")
    atrbts = atrbt.split()
    if len(atrbts) > 3:
        raise HubAttributeError(line_num, "")
    for word in atrbts:
        if word.startswith("zone"):
            a_zone += 1
        elif word.startswith("color"):
            a_color += 1
        elif word.startswith("max_drones"):
            a_drone += 1
        if any(i >= 2 for i in [a_drone, a_color, a_zone]):
            raise HubAttributeError(line_num, "")
        update = export_data(word, line_num, state)
        attribute_dict.update(update.data)
    return attribute_dict


@register_exporter("color")
def _get_color(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    """Parse a ``color=<name>`` attribute.

    Args:
        line: Attribute token of the form ``color=<name>``.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator (unused).

    Returns:
        A :class:`ParseUpdate` carrying the validated color.

    Raises:
        ParserError: If the color value fails validation.
    """
    title, _, info = line.partition("=")
    color = validate_color(info, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE, data={"color": color}, line_num=line_num
    )


@register_exporter("zone")
def _get_zone_atrbt(
    line: str, line_num: int, state: ParseState
) -> ParseUpdate:
    """Parse a ``zone=<type>`` attribute.

    Validates the zone type against the allowed values (e.g.
    ``zone=restricted``) and wraps it as a :class:`ZoneType`.

    Args:
        line: Attribute token of the form ``zone=<type>``.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator (unused).

    Returns:
        A :class:`ParseUpdate` carrying the validated :class:`ZoneType`.

    Raises:
        ParserError: If the zone value fails validation.
    """
    _, _, info = line.partition("=")
    zone = validate_zone(info, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"zone_type": ZoneType(zone)},
        line_num=line_num,
    )


@register_exporter("max_drones")
def _get_max_drone_nb(
    line: str, line_num: int, state: ParseState
) -> ParseUpdate:
    """Parse a ``max_drones=<n>`` attribute.

    Args:
        line: Attribute token of the form ``max_drones=<n>``.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator (unused).

    Returns:
        A :class:`ParseUpdate` carrying the maximum drone count.

    Raises:
        ValueRangeError: If the value is not a non-negative integer.
    """
    _, _, nb_drone = line.partition("=")
    try:
        nb_drones = int(nb_drone)
    except (TypeError, ValueError):
        raise ValueRangeError(
            line_num, "max_drones", "should be positive integer"
        )
    if nb_drones < 0:
        raise ValueRangeError(
            line_num, "max_drones", "should be positive integer"
        )
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"max_drones": nb_drones},
        line_num=line_num
    )


@register_exporter(ConfigKeyWords.CONNECTION)
def _get_connection_info(
    line: str, line_num: int, state: ParseState
) -> ParseUpdate:
    """Parse a ``connection: <a>-<b> [..]`` line.

    Handles both the bare ``<a>-<b>`` form and the form with a trailing
    bracketed attribute.

    Args:
        line: Raw input line.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator, used to validate zone names.

    Returns:
        A :class:`ParseUpdate` describing the connection endpoints and any
        parsed attribute.

    Raises:
        ConnectionFormatError: If the endpoint format is wrong, the names do
            not match existing zones, or the attribute is malformed.
    """
    title, _, info = line.partition(": ")
    if "[" not in info:  # if no attributes
        # infos = info.split("-")
        infos = _check_connection_format(line_num, info, state)
        return ParseUpdate(
            target=ConfigKeyWords.CONNECTION,
            data={
                ConfigKeyWords.ORIGIN: infos[0], ConfigKeyWords.TO: infos[1]
            },
            line_num=line_num,
        )
    info, _, attrbt = info.partition(" [")  # with attributes
    infos = _check_connection_format(line_num, info, state)
    attribute = _get_connection_attribute(attrbt, line_num, state)
    return ParseUpdate(
        target=ConfigKeyWords.CONNECTION,
        data=({
            ConfigKeyWords.ORIGIN: infos[0], ConfigKeyWords.TO: infos[1]
        } | attribute
        ),
        line_num=line_num,
    )


def _check_connection_format(
    line_num: int, info: str, state: ParseState
) -> list[str]:
    """Validate the ``<a>-<b>`` endpoint part of a connection.

    Args:
        line_num: 1-based line number for error reporting.
        info: The endpoint text, expected to be ``<origin>-<to>``.
        state: Current parsing accumulator, used to verify the zone names
            exist.

    Returns:
        The two endpoint names as ``[origin, to]``.

    Raises:
        ConnectionFormatError: If the text does not split into exactly two
            names, or a name does not match an existing zone.
    """
    infos = info.split("-")
    if len(infos) != 2:
        raise ConnectionFormatError(
            line_num, "Connection format error"
        )
    if not all(con_name in state.zone_names for con_name in infos):
        raise ConnectionFormatError(
            line_num,
            "Connection name error: name doesn't match existing zone names"
        )
    return infos


def _get_connection_attribute(
        line: str, line_num: int, state: ParseState
) -> dict[str, str]:
    """Parse the ``max_link_capacity=<n>`` attribute of a connection.

    Args:
        line: Attribute text, optionally still wrapped in a trailing ``]``.
        line_num: 1-based line number for error reporting.
        state: Current parsing accumulator (unused).

    Returns:
        A dict mapping ``"max_link_capacity"`` to its string value.

    Raises:
        ConnectionFormatError: If the key is misspelled, the value is not an
            integer, or the value is less than 1.
    """
    zones = line.strip("]")
    title, _, max_num = zones.partition("=")
    if title != "max_link_capacity":
        raise ConnectionFormatError(
            line_num, "Attribute spelling error, "
            "it should be 'max_link_capacity=<int>'")
    try:
        capacity = int(max_num)
    except ValueError:
        raise ConnectionFormatError(
            line_num, "max_link_capacity must be an integer"
        )
    if capacity < 1:
        raise ConnectionFormatError(line_num, "max_link_capacity "
                                    "should be greater than or equal to 1")
    return {title: max_num}
