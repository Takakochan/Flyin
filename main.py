import argparse

from find_path import CBSSolver
from parser import parser, select_file, ParserError
from graph import GraphValidationError
from find_path import PathNotFoundError


def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="Drone pathfinding simulator"
    )
    arg_parser.add_argument("map_file", nargs="?", default=None,
                            help="path to map file")
    arg_parser.add_argument("--capacity-info", action="store_true",
                            help="print zone/connection capacity usage per turn")
    args = arg_parser.parse_args()

    format_txt_file()
    file = args.map_file if args.map_file else select_file()
    graph = parser(file)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    try:
        solver.solve(capacity_info=args.capacity_info)
    except RuntimeError:
        solver.solve2()


def format_txt_file() -> None:
    file_name = "Dron_paths.txt"
    with open(file_name, "w", encoding="utf-8") as _:
        pass


if __name__ == "__main__":
    try:
        main()
        print("Program succesfully finished!!")
    except (
        ParserError,
        GraphValidationError,
        ValueError,
        PathNotFoundError
    ) as e:
        print(f" {type(e).__name__}: {e}")
