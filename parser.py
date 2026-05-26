import glob
import inquirer  # type: ignore[import-untyped]
from typing import Any
from collections.abc import Callable
from functools import wraps

from graph import Graph
from zone import Zone
from location import Position


type ExportFn = Callable[[str, int], Any]

exporters = dict[str, ExportFn] = {}
class ParserError(Exception):
    pass

def register_exporter(key_word: str) -> Callable:
    def decorator(func: ExportFn) -> ExportFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        exporters[key_word] = wrapper
        return wrapper
    return decorator



def select_file(cls) -> str:
    dir_path = glob.glob("maps/**/*.txt")
    question = [
        inquirer.List(
            "file",
            message="which file would like to try?",
            choices=dir_path,
        )
    ]
    answers = inquirer.prompt(question)
    if not answers:
        raise ValueError("No file selected")
    selected = answers["file"]
    print(f"The file  {selected} is selected")
    return selected


def parser(file_path: str) -> Graph:
    graph = Graph()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                export_data(line, line_num, graph)
    except FileNotFoundError:
        raise ValueError(f"file not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    return graph

def export_data(line: str, line_num: int, graph) -> Graph:
    title, sep, info = line.partition(':')
    exporter = exporters.get(title)
    if exporter is None:
        raise ParserError(f"Line: {line_num} no exporter found in the format")
    exporter(line, line_num)

@register_exporter("nb_drones:")
def _nb_drone(self, line: str, line_num: int) -> int:
    words = line.split()
    if len(words) != 2:
        raise ParserError(f"Line {line_num}: expected form"
                         f" 'nb_drones: <positive num>'")
    try:
        nb_drone = int(words[1])
    except (ValueError, TypeError):
        raise ParserError(f"Line {line_num}: THe format is not as expected")
    if nb_drone <= 0:
        raise ParserError("Number of drones must be positive")
    return nb_drone

@register_exporter("start_hub")
@register_exporter("hub")
@register_exporter("end_hub")
def _properhub(self, line: str, line_num: int) -> Zone:
    zone_dict: Zone = {}
    try:
        # if int(line.find("]")) != len(line):
        if not line.endswith("]"):
            raise ParserError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
        if "[" in line and "]" in line:
            strt = line.find('[')
            attrbt = line[strt:]
            # dict_attribt = self._get_attribute(attrbt)
        new_line = line[:strt]
        print(new_line)
        words = new_line.split()
        if len(words) != 4:
            raise ParserError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
    except ValueError:
        raise ('Some error')
    
    return zone_dict

@register_exporter("connection")
def _get_connection_info(line: str, line_num: int) -> None:
    words = line.split()
    if len(words) < 2:
        raise ParserError('wrong format')


# def _get_attribute(line: str) -> None:
#     if '[' not in line:
#         raise

if __name__ == "__main__":
    try:
        file_path = select_file()
        parser(file_path)
    except ParserError as e:
        print(f"Error: {e}")



"""
• Zone definition on each line using type prefixes:
◦ start_hub:
◦ end_hub:
◦ hub:
<name> <x> <y> [metadata] marks the starting zone.
<name> <x> <y> [metadata] marks the end zone.
<name> <x> <y> [metadata] defines a regular zone.
◦ The connection syntax forbids dashes in zone names (see below).
• All metadata is optional and enclosed in brackets [...] with default values:
◦ zone=<type> (default: normal)
◦ color=<value> (default: none)
◦ max_drones=<number> (default: 1) - Maximum drones that can occupy this
zone simultaneously
◦ Tags inside brackets can appear in any order.
"""