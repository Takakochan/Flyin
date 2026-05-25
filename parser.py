import glob
import inquirer  # type: ignore[import-untyped]
from dataclasses import dataclass
from typing import NamedTuple
from graph import Graph
from zone import Zone

# class HubFormatError(Exception):
#     def __init__(self, value, message='Hub must be discribed Hub_name int int [attributes]') -> None:


class Position(NamedTuple):
    x: int
    y: int


@dataclass
class Parser:
    filepath: str

    @classmethod
    def select_file(cls) -> "Parser":
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
        return cls(filepath=selected)

    def parser(self) -> Graph:
        graph = Graph()
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    self._parse_line(line, line_num, graph)
        except FileNotFoundError:
            raise ValueError(f"file not found: {self.filepath}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {self.filepath}")
        return graph
    
    def _parse_line(self, line: str, line_num: int, graph: Graph) -> None:
        if line.startswith('nb_drones:'):
            self._nb_drone(line, line_num)
        elif line.startswith('start_hub:'):
            self._properhub(line, line_num)
        elif line.startswith('end_hub:'):
            self._properhub(line, line_num)
        elif line.startswith('hub:'):
            self._properhub(line, line_num)
        elif line.startswith('connection:'):
            self.connection_format(line, line_num)

    def _nb_drone(self, line: str, line_num: int) -> int:
        try:
            words = line.split()
            if len(words) != 2:
                raise ValueError(f"Lini {line_num}: expected form"
                                 f" 'nb_drones: <positive num>'")
            nb_drone = words[1]
            if nb_drone <= 0:
                raise ValueError("Number of drones must be positive")
            return nb_drone
        except (ValueError, TypeError):
            raise ValueError(f"Line {line_num}: The format is not as expected")

    def _properhub(self, line: str, line_num: int) -> Zone:
        zone_dict: Zone = {}
        try:
            # if int(line.find("]")) != len(line):
            if not line.endswith("]"):
                raise ValueError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
            if "[" in line and "]" in line:
                strt = line.find('[')
                attrbt = line[strt:]
                dict_attribt = self._get_attribute(attrbt)
            new_line = line[:strt]
            print(new_line)
            words = new_line.split()
            if len(words) != 4:
                raise ValueError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
        except:
            something()
        
        return zone_dict

    def _get_attribute(attrbt: str) -> dict:
        try: 
            



if __name__ == "__main__":
    parser = Parser.select_file()
    parser.parse()



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