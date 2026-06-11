import glob
import inquirer  # type: ignore[import-untyped]
from collections.abc import Callable
from typing import Any
from functools import wraps
from dataclasses import dataclass
from enum import StrEnum, auto


from graph import Graph
from zone import Zone, ZoneType, Position
from connection import Connection
from draw_map import DrawConnection


type ExportFn = Callable[[str, int], Any]
type SetterFn = Callable[[ConfigKeyWords, list, int], Any]


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
    zones: list[dict]
    zone_names: set[str]
    connections: list[dict]
    connection_seen: set[frozenset[str]]
    nb_drones: int


@dataclass
class ParseUpdate:
    target: str
    data: dict


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
            "Expected 'connection: <name of hub>-<name of hub> "
            "[Optionl-<max_link_capacity=positive int>]'"
        )


@dataclass
class UnknownKeyError(ParserError):
    line_num: int
    keyword: str

    def __str__(self):
        return f"Line {self.line_num}: Unknown keyword '{self.keyword}"


@dataclass
class ValueRangeError(ParserError):
    line_num: int
    field: str
    detail: str

    def __str__(self):
        return f"Line {self.line_num}: [{self.field}] {self.detail}"


@dataclass
class DupplicatedConnectionError(ParserError):
    line_num: int
    fig: list
    detail: str

    def __str__(self):
        return f"Line {self.line_num}: [{self.fig}] {self.detail} "


@dataclass
class ZoneNameError(ParserError):
    line_num: int
    fig: str
    detail: str

    def __str__(self):
        return f"Line {self.line_num}: [{self.fig}] {self.detail} "


def register_exporter(key_word: str) -> Callable:
    def decorator(func: ExportFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # print(f"DEBUG:::{func.__name__}")
            return func(*args, **kwargs)

        EXPORTERS[key_word] = wrapper
        return wrapper

    return decorator


def setter_machine(name: ConfigKeyWords) -> Callable:
    def decorator(func: SetterFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> list:
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
    selected = answers["Choose a file"]
    print(f"The file {selected} is selected")
    return selected


def parser(file_path: str) -> Graph:
    state = ParseState(
        zones=[],
        zone_names=set(),
        connections=[],
        connection_seen=set(),
        nb_drones=0,
    )
    to_list = []
    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("\n"):
                    continue

                fetched = export_data(line, line_num)
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
    return Graph(
        zones={dat[ConfigKeyWords.NAME]: Zone(**dat) for dat in state.zones},
        connections=[Connection(**cnc) for cnc in state.connections],
        nb_drone=state.nb_drones,
    )


def handle_zone(state: ParseState, fetched: ParseUpdate, line_num: int):
    name = fetched.data[ConfigKeyWords.NAME]
    if name in state.zone_names:
        raise ZoneNameError(
            line_num=line_num,
            fig=name,
            detail="is dupplicated"
        )
    state.zone_names.add(name)
    state.zones.append(fetched.data)


def handle_connection(state: ParseState, fetched: ParseUpdate, line_num: int):
    pair = frozenset(
        {
            fetched.data[ConfigKeyWords.ORIGIN],
            fetched.data[ConfigKeyWords.TO],
        }
    )
    if pair in state.connection_seen:
        raise DupplicatedConnectionError(
            line_num=line_num, fig=list(pair), detail="already exist"
        )
    state.connection_seen.add(pair)
    state.connections.append(fetched.data)


def export_data(line: str, line_num: int) -> ParseUpdate:
    for sep in SEPARATORS:
        if sep in line:
            title, _, info = line.partition(sep)
            exporter = EXPORTERS.get(title)
            if exporter is None:
                raise HubFormatError(
                    line_num=line_num,
                    detail="unexpected format"
                )
            fetched_data = exporter(line, line_num)
            return fetched_data
    raise HubFormatError(line_num=line_num, detail="unexpected format")


@register_exporter("nb_drones")
def _get_nb_drones(line: str, line_num: int) -> ParseUpdate:
    words = line.split()
    if len(words) != 2:
        raise FormatError(
            line_num=line_num,
            detail="the for mat is expected:: 'nb_drones: <positive number>'",
        )
    nb_drones = int(words[1])
    if nb_drones <= 0:
        raise ValueRangeError(
            line_num=line_num, field="nb_drones", detail="must be positive"
        )
    return ParseUpdate(
        target=ConfigKeyWords.NB_DRONE,
        data={"nb_drones": nb_drones}
    )


@register_exporter("start_hub")
@register_exporter("end_hub")
@register_exporter("hub")
def _get_zone_info(line: str, line_num: int) -> ParseUpdate:
    if "[" not in line and "]" not in line:
        raise HubFormatError(
            line_num=line_num,
            detail="Attribute is not given"
        )
    hub, _, attrb = line.partition("[")
    hubs = hub.split()
    if len(hubs) != 4:
        raise HubFormatError(line_num=line_num, detail="wrong format")
    role = hubs[0].strip(":")
    role, _, _ = role.partition("_")
    name = hubs[1].strip()
    x = int(hubs[2])
    y = int(hubs[3])
    attribute_dict = _get_attribute(attrb, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data=(
            {
                "zone_role": role,
                ConfigKeyWords.NAME: name,
                "position": Position(x=x, y=y),
            } | attribute_dict
        ),
    )


def _get_attribute(atrbt: str, line_num: int) -> dict:
    attribute_dict = {}
    atrbt = atrbt.strip("]")
    atrbts = atrbt.split()
    for word in atrbts:
        update = export_data(word, line_num)
        attribute_dict.update(update.data)
    return attribute_dict


@register_exporter("color")
def _get_color(line: str, line_num: int) -> ParseUpdate:
    title, _, info = line.partition("=")
    return ParseUpdate(target=ConfigKeyWords.ZONE, data={title: info})


@register_exporter(ConfigKeyWords.ZONE)
def _get_zone_atrbt(line: str, line_num: int) -> ParseUpdate:
    """
    check one of those attributes ex)zone=restricted color=darkred max_drones=1
    """
    _, _, info = line.partition("=")
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"zone_type": ZoneType(info)}
    )


@register_exporter("max_drones")
def _get_max_drone_nb(line: str, line_num: int) -> ParseUpdate:
    _, _, nb_drone = line.partition("=")
    try:
        nb_drones = int(nb_drone)
    except (TypeError, ValueError):
        raise ValueRangeError(
            line_num=line_num,
            field="max_drones",
            detail="should be positive integer"
        )
    if nb_drones <= 0:
        raise ValueRangeError(
            line_num=line_num,
            field="max_drones",
            detail="should be positive integer"
        )
    return ParseUpdate(
        target=ConfigKeyWords.ZONE,
        data={"max_drones": nb_drones}
    )


@register_exporter(ConfigKeyWords.CONNECTION)
def _get_connection_attribute(line: str, line_num: int) -> ParseUpdate:
    try:
        title, _, info = line.partition(": ")
    except ParserError:
        raise ConnectionFormatError(line_num=line_num, detail="")
    if "[" not in info:  # if no attributes
        infos = info.split("-")
        if len(infos) != 2:
            raise ConnectionFormatError(
                line_num=line_num,
                detail="wrong format"
            )
        return ParseUpdate(
            target=ConfigKeyWords.CONNECTION,
            data={ConfigKeyWords.ORIGIN: infos[0],
                  ConfigKeyWords.TO: infos[1]},
        )
    info, _, attrbt = info.partition(" [")  # with attributes
    infos = info.split("-")
    if len(infos) != 2:
        raise ConnectionFormatError(
            line_num=line_num, detail="wrong format in attributes"
        )
    attribute = _get_connection_attribute(attrbt, line_num)
    return ParseUpdate(
        target=ConfigKeyWords.CONNECTION,
        data=(
            {
                ConfigKeyWords.ORIGIN: infos[0],
                ConfigKeyWords.TO: infos[1]
            } | attribute
        ),
    )


#@register_exporter("max_link_capacity")
def _get_connection_attribute(line: str, line_num: int) -> dict:
    zones = line.strip("]")
    title, _, max_num = zones.partition("=")
    return {title: max_num}


if __name__ == "__main__":
    try:
        file = select_file()
        graph = parser(file)
        print(graph)
        DrawConnection.draw(graph)

    except ParserError as e:
        print(e)
        exit(1)
