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
    zones: list[dict[str, Any]]
    zone_names: set[str]
    connections: dict[tuple[str, str], dict[str, Any]]
    connection_seen: set[frozenset[str]]
    nb_drones: int


@dataclass
class ParseUpdate:
    target: str
    data: dict[str, Any]
    line_num: int


class ParserError(Exception):
    """base"""

    pass


@dataclass
class FormatError(ParserError):
    line_num: int
    detail: str

    def __str__(self) -> str:
        return f"Line {self.line_num}: {self.detail}"


@dataclass
class HubAttributeError(ParserError):
    line_num: int
    details: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.details} Expected atributes "
            "ex) [zone=restricted color=maroon max_drones=2]"
        )


@dataclass
class HubFormatError(ParserError):
    line_num: int
    detail: str

    def __str__(self) -> str:
        return (
            f"Line {self.line_num}: {self.detail}. "
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
            #"Expected 'connection: <name of hub>-<name of hub> "
            #"[Optionl-<max_link_capacity=positive int>]'"
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
    def decorator(func: ExportFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        EXPORTERS[key_word] = wrapper
        return wrapper

    return decorator


def setter_machine(name: ConfigKeyWords) -> Callable[[SetterFn], ExportFn]:
    def decorator(func: SetterFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        SETTERS[name] = wrapper
        return wrapper

    return decorator


def select_file() -> str:
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
    if "[" not in line or "]" not in line:
        raise HubFormatError(
            line_num, "Attribute is not given"
        )
    hub, _, attrb = line.partition("[")
    hubs = hub.split()
    if len(hubs) != 4:
        raise HubFormatError(line_num, "wrong format")
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
    if len(attribute_dict) <= 0:
        raise HubAttributeError(line_num, "Attribute is not given")
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
    title, _, info = line.partition("=")
    color = validate_color(info, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE, data={"color": color}, line_num=line_num
    )


@register_exporter("zone")
def _get_zone_atrbt(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    """
    check one of those attributes ex) zone=restricted color=darkred max_drones=1
    """
    _, _, info = line.partition("=")
    zone = validate_zone(info, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"zone_type": ZoneType(zone)},
        line_num=line_num,
    )


@register_exporter("max_drones")
def _get_max_drone_nb(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    _, _, nb_drone = line.partition("=")
    try:
        nb_drones = int(nb_drone)
    except (TypeError, ValueError):
        raise ValueRangeError(
            line_num, "max_drones", "should be positive integer"
        )
    if nb_drones <= 0:
        raise ValueRangeError(
            line_num, "max_drones", "should be positive integer"
        )
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"max_drones": nb_drones},
        line_num=line_num
    )


@register_exporter(ConfigKeyWords.CONNECTION)
def _get_connection_info(line: str, line_num: int, state: ParseState) -> ParseUpdate:
    title, _, info = line.partition(": ")
    if "[" not in info:  # if no attributes
        infos = info.split("-")
        if len(infos) != 2:
            raise ConnectionFormatError(
                line_num, "wrong format"
            )
        unknown = [name for name in infos if name not in state.zone_names]
        if unknown:
            raise ConnectionFormatError(
                line_num, f"Unknown zone name(s) {', '.join(unknown)}"
            )
        return ParseUpdate(
            target=ConfigKeyWords.CONNECTION,
            data={
                ConfigKeyWords.ORIGIN: infos[0], ConfigKeyWords.TO: infos[1]
            },
            line_num=line_num,
        )
    info, _, attrbt = info.partition(" [")  # with attributes
    infos = info.split("-")
    if not all(con_name in state.zone_names for con_name in infos):
        raise ConnectionFormatError(
            line_num, "wrong format in attributes"
        )
    attribute = _get_connection_attribute(attrbt, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.CONNECTION,
        data=({
            ConfigKeyWords.ORIGIN: infos[0], ConfigKeyWords.TO: infos[1]
        } | attribute
        ),
        line_num=line_num,
    )


def _get_connection_attribute(line: str, line_num: int) -> dict[str, str]:
    zones = line.strip("]")
    title, _, max_num = zones.partition("=")
    if title != "max_link_capacity":
        raise ConnectionFormatError(
            line_num, "Attribute spelling error, "
            "it should be 'max_link_capacity=<int>'")
    if int(max_num) < 1:
        raise ConnectionFormatError(line_num, "max_link_capacity "
                                    "should be greater than or equal to 1")
    return {title: max_num}
