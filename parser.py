import glob
import inquirer  # type: ignore[import-untyped]
from dataclasses import dataclass
from typing import NamedTuple

from graph import Graph
from zone import Zone
from location import Position


class ParserError(Exception):
    pass


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
        # elif line.startswith('connection:'):
            # self.connection_format(line, line_num)

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

    def _properhub(self, line: str, line_num: int) -> Zone:
        if not line.endswith("]"):
            raise ParserError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
        if "[" in line and "]" in line:
            zone, sep, attrbt = line.partition('[')
            
            # dict_attribt = self._get_attribute(attrbt)
        
        print(zone)
        words = zone.split()
        if len(words) != 4:
            raise ParserError(f"Line {line_num}: Expected format is '<optional_>hub: <name_of_hub> <num> <num>  [attributes]'")
        try:
            x = int(words[2])
            y = int(words[3])
        except ValueError:
            raise ParserError(f"Line {line_num}: x and y must be integers")
        
        return Zone(
            name=words[1],
            position=Position(x=x, y=y),
        )




if __name__ == "__main__":
    try:
        parser = Parser.select_file()
        parser.parser()
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

"""
Pydantic の BaseModel の仕組みから説明します。

  ---
  普通の Python クラスとの違い
  
  普通のクラスなら __init__ を自分で書きますが、BaseModel を継承すると
   Pydantic が自動でやってくれます。

  # Zone の定義
  class Zone(BaseModel):
      name: str
      position: Position
      color: str | None = None

  これを見た Pydantic は自動的に：
  - name と position は必須
  - color はオプション（デフォルト None）

  という __init__ を生成します。

  ---
  作り方

  # ✅ Pydantic の作り方
  zone = Zone(name="waypoint1", position=Position(x=1, y=0))

  # ❌ dict は Zone ではない（型が違う）
  zone_dict: Zone = {}
  zone_dict['name'] = "waypoint1"  # Zone オブジェクトに [] 
  でアクセスはできない

  ---
  Pydantic の嬉しいところ

  作るときにバリデーションも自動で走ります：

  Zone(name="waypoint1", position=Position(x="abc", y=0))
  # → エラー！x は int でなければならない

  zone.py の max_drones: int = Field(default=1, ge=1) の ge=1 は「1以
  上でなければならない」という制約で、これも自動でチェックされます。

  ---
  まとめると、Zone(...) はクラスのインスタンスを作る呼び出しで、dict
  の {} とは全く別物です。
"""