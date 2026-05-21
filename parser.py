import glob
import inquirer  # type: ignore[import-untyped]
from dataclasses import dataclass
from typing import NamedTuple
from graph import Graph

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
        if line.startwith('nb_drones:'):
            self.nb_drone(line, line_num)
        elif line.startwith('start_hub:'):
            self.properhub(line, line_num)
        elif line.startwith('end_hub:'):
            self.properhub(line, line_num)
        elif line.startwith('hub:'):
            self.properhub(line, line_num)
        elif line.startswith('connection:'):
            self.connection_format(line, line_num)




if __name__ == "__main__":
    parser = Parser.select_file()
    parser.parse()
