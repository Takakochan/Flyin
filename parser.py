import glob
import inquirer  # type: ignore[import-untyped]
from collections.abc import Callable
from typing import Any
from functools import wraps

from graph import Graph
from zone import Zone


type ExportFn = Callable[[str], Any]

exporters: dict[str, ExportFn] = {}


class ParserError(Exception):
    pass


def register_exporter(key_word: str) -> Callable:
    def decorator(func: ExportFn):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        exporters[key_word] = wrapper
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


def parser(file_path: str) -> None:
    # graph = Graph(zones={}, connections=[])
    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                if not line or line.startswith('#') or line.startswith('\n'):
                    continue
                line = line.strip()
                export_data(line, line_num)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    # return graph


def export_data(line: str, line_num: int) -> None:
    title, sep, info = line.partition(':')
    exporter = exporters.get(title)
    if exporter is None:
        raise ParserError(f"Line: {line_num} No exporter fount for the format")
    exporter(line, line_num)

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
def _get_zone_info(line: str, line_num: int) -> None: # only normal zone
    # zone = Zone()
    if '[' not in line and ']' not in line:
        raise ParserError(f"Line {line_num}: Attribute is not given")
    hub, sep, attrb = line.partition('[')
    print(hub)
    print(attrb)
    # Graph.zones


@register_exporter("connection")
def _get_connection_info(line: str, line_num: int) -> None:
    words = line.split()
    if len(words) < 2:
        raise ParserError('wrong format')



# def _get_startzone_info(self, line, line_num) -> Zone:
#     zone = Zone()
# def _get_attribute(line: str) -> None:
#     if not '[' in line:
#         raise



"""
class Zone(BaseModel):
    name: str
    position: Position
    max_drones: int = Field(default=1, ge=1)
    zone_type: ZoneType.NORMAL
    color: str | None = None
"""




if __name__ == "__main__":
    try:
        file = select_file()
        parser(file)
    except ParserError as e:
        raise (e)
