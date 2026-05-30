import glob
import inquirer  # type: ignore[import-untyped]
from collections.abc import Callable
from typing import Any
from functools import wraps
from dataclasses import dataclass
from pprint import pprint


from graph import Graph
from zone import Zone, ZoneType, Position
from connection import Connection


type ExportFn = Callable[[str, int], Any]

EXPORTERS: dict[str, ExportFn] = {}
SEPARATORS = (":", "[", "=")


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
        return (
            f"Line {self.line_num}: "
            f"{self.detail}"
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
    nb_drone_dic = {}
    zone_dict = []
    zone_names = []
    connection_dict = []
    zone_connection_checker = [list[str, str]]
    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("\n"):
                    continue

                update = export_data(line, line_num)
                if update.target == "Zone":
                    zone_dict.append(update.data)
                    the_name = update.data["name"]
                    if the_name in zone_names:
                        raise ZoneNameError(
                            line_num=line_num,
                            fig=the_name,
                            detail="is dipplicated"
                        )
                    zone_names.append(update.data["name"])
                elif update.target == "nbdrone":
                    nb_drone_dic.update(update.data)
                elif update.target == "Connection":
                    for zone in [update.data["origin"], update.data["to"]]:
                        if zone not in zone_names:
                            raise ZoneNameError(
                                line_num=line_num,
                                fig=zone,
                                detail="is mistyped"
                            )
                    connection_comb = sorted(
                        [update.data["origin"], update.data["to"]]
                    )
                    if connection_comb in zone_connection_checker:
                        raise DupplicatedConnectionError(
                            line_num=line_num,
                            fig=connection_comb,
                            detail="combination already exist"
                        )
                    zone_connection_checker.append(connection_comb)

                    """sketch of connections dupplication and error


                    """
                    connection_dict.append(update.data)

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    print("=== ZONE DATA ===")
    pprint(zone_dict)
    print("+++++NAMES+++++")
    pprint(zone_names)
    print("=== CONNETION DATA ===")
    pprint(connection_dict)
    print("=== GRAPH DATA ===")
    pprint(nb_drone_dic)

    return Graph(
        zones={data["name"]: Zone(**data) for data in zone_dict},
        connections=[Connection(**cnc) for cnc in connection_dict],
        nb_drone=nb_drone_dic["nb_drones"],
    )


def export_data(line: str, line_num: int) -> ParseUpdate:
    for sep in SEPARATORS:
        # print(f"DEBUG tyring a separator '{sep}'")
        if sep in line:
            title, _, info = line.partition(sep)
            exporter = EXPORTERS.get(title)
            if exporter is None:
                raise HubFormatError(
                    line_num=line_num,
                    detail="unexpected format"
                )
            update = exporter(line, line_num)
            return update
    raise HubFormatError(
        line_num=line_num,
        detail="unexpected format"
    )


@register_exporter("nb_drones")
def _get_nb_drones(line: str, line_num: int) -> ParseUpdate:
    words = line.split()
    if len(words) != 2:
        raise FormatError(
            line_num=line_num,
            detail="the for mat is expected:: 'nb_drones: <positive number>'"
        )
    nb_drones = int(words[1])
    if nb_drones <= 0:
        raise ValueRangeError(
            line_num=line_num,
            field="nb_drones",
            detail="must be positive"
        )
    return ParseUpdate(target="nbdrone", data={"nb_drones": nb_drones})


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
        raise HubFormatError(
            line_num=line_num,
            detail="wrong format"
        )
    role = hubs[0].strip(":")
    role, _, _ = role.partition("_")
    name = hubs[1].strip()
    x = int(hubs[2])
    y = int(hubs[3])
    attribute_dict = _get_attribute(attrb, line_num)
    return ParseUpdate(
        target="Zone",
        data=(
            {"zone_role": role, "name": name, "position": Position(x=x, y=y)} | attribute_dict
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
    return ParseUpdate(target="Zone", data={title: info})


@register_exporter("zone")
def _get_zone_atrbt(line: str, line_num: int) -> ParseUpdate:
    """
    check one of those attributes ex)zone=restricted color=darkred max_drones=1
    """
    _, _, info = line.partition("=")
    return ParseUpdate(target="Zone", data={"zone_type": ZoneType(info)})


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
    if nb_drones < 0:
        raise ValueRangeError(
            line_num=line_num,
            field="max_drones",
            detail="should be positive integer"
        )
    return ParseUpdate(target="Zone", data={"max_drones": nb_drones})


@register_exporter("connection")
def _get_connection_info(line: str, line_num: int) -> ParseUpdate:
    try:
        title, _, info = line.partition(": ")
    except ParserError:
        raise ConnectionFormatError(
            line_num=line_num,
            detail=""
        )
    if "[" not in info:  # if no attributes
        infos = info.split("-")
        if len(infos) != 2:
            raise ConnectionFormatError(
                line_num=line_num, detail="wrong format"
            )
        return ParseUpdate(
            target="Connection", data={"origin": infos[0], "to": infos[1]}
        )
    info, _, attrbt = info.partition(" [")  # with attributes
    infos = info.split("-")
    if len(infos) != 2:
        raise ConnectionFormatError(
            line_num=line_num, detail="wrong format in attributes"
        )
    attribute = _get_connection_attribute(attrbt, line_num)
    return ParseUpdate(
        target="Connection", data=({"origin": infos[0], "to": infos[1]} | attribute)
    )


@register_exporter("max_link_capacity")
def _get_connection_attribute(line: str, line_num: int) -> dict:
    zones = line.strip("]")
    title, _, max_num = zones.partition("=")
    return {title: max_num}


if __name__ == "__main__":
    try:
        file = select_file()
        parser(file)
    except ParserError as e:
        print(e)
        exit(1)


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
