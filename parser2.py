import glob
import inquirer  # type: ignore[import-untyped]
from collections.abc import Callable
from typing import Any
from functools import wraps

from graph import Graph
from zone import Zone, ZoneType, ZoneRole, ZoneState, Position


type ExportFn = Callable[[str, int], Any]

EXPORTERS: dict[str, ExportFn] = {}
SEPARATORS = (':', '[]', '=')


class ParserError(Exception):
    pass


def register_exporter(key_word: str) -> Callable:
    def decorator(func: ExportFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            print(func.__name__)
            return func(*args, **kwargs)
        EXPORTERS[key_word] = wrapper
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
    graph = Graph(zones={}, connections=[])
    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('\n'):
                    continue
                print(line_num)
                export_data(line, line_num)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    return graph


def export_data(line: str, line_num: int) -> None:
    for sep in SEPARATORS:
        if sep in line:
            title, _, info = line.partition(sep)
            exporter = EXPORTERS.get(title)
            if exporter is None:
                raise ParserError(f"Line: {line_num} No exporter found for the format")
            exporter(line, line_num)
            return
    raise ParserError(f"No valid separator found: {line}")
    
    


@register_exporter("nb_drones")
def _get_nb_drones(line: str, line_num: int) -> int:
    words = line.split()
    if len(words) != 2:
        raise ParserError('wrong format')
    nb_drones = int(words[1])
    if nb_drones <= 0:
        raise ParserError(f"Line {line_num}: Number of drones must be positive")
    print(f"Number of drones are: {nb_drones}")
    return nb_drones


@register_exporter("start_hub")
@register_exporter("end_hub")
@register_exporter("hub")
def _get_zone_info(line: str, line_num: int) -> Zone:
    if '[' not in line and ']' not in line:
        raise ParserError(f"Line {line_num}: Attribute is not given")
    hub, _, attrb = line.partition('[')
    hubs = hub.split()
    if len(hubs) < 4:
        raise ParserError(f"Line {line_num}: missing information")
    # print(hubs[0])
    if hubs[0] == 'start_hub:':
        role = ZoneRole.START
    elif hubs[0] == 'end_hub:':
        role = ZoneRole.END
    elif hubs[0] == 'hub:':
        role = ZoneRole.HUB
    name = hubs[1].strip()
    x = int(hubs[2])
    y = int(hubs[3])
    print(role)
    # _get_attribute(attrb, line_num)
    return Zone(zone_role=role, name=name, position=Position(x=x, y=y))


@register_exporter("connection")
def _get_connection_info(line: str, line_num: int) -> None:
    words = line.split()
    if len(words) < 2:
        raise ParserError('wrong format')


def _get_attribute(atrbt: str, line_num: int) -> None:
    print('_get_attribute')
    atrbt = atrbt.strip(']')
    atrbts = atrbt.split()
    for word in atrbts:
        export_data(word, line_num)


# @register_exporter("color")
# def _get_color():

@register_exporter("zone")  #check one of those zone=restricted color=darkred max_drones=1
def _get_zone_atrbt(word: str, line_num: int) -> ZoneType:
    return ZoneType(word)


@register_exporter("max_drones")
def _get_max_drone_nb(word: str, line_num: int) -> Zone:
    try:
        nb_drones = int(word)
    except (TypeError, ValueError):
        raise ValueError(f"Line {line_num}: should be positive number")
    if nb_drones < 0:
        raise ValueError(f"Line {line_num}: should be positive number")
    return Zone(max_drones=nb_drones)

"""
class Graph(BaseModel):
    zones: dict[str, Zone]
    connections: list[Connection]
    start: Zone | None = None
    goal: Zone | None = None
    nb_drone: int = 0
class Zone(BaseModel):
    name: str
    position: Position
    max_drones: int = Field(default=1, ge=1)
    zone_type: ZoneType.NORMAL
    color: str | None = None

hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

    # def a(name, pos)

    # t = (1, 2, 3)
    # a((1, 2, 3))
    # d = {"name": "steve", "pos": (1, 3)}
    # a(**d)
    # a(name="steve", pos=(1, 3))
    # a(pos=(1,5))
"""

if __name__ == "__main__":
    try:
        file = select_file()
        parser(file)
    except ParserError:
        raise ParserError("error")
