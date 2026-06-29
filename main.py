from find_path import CBSSolver
from parser import parser, select_file, ParserError
from graph import GraphValidationError
from find_path import PathNotFoundError


def main() -> None:
    format_txt_file()
    print("+x+x+x  Fly-in  x+x+x+")
    file = select_file()
    graph = parser(file)
    solver = CBSSolver(graph)
    try:
        solver.solve()
    except RuntimeError:
        solver.solve2()


def format_txt_file() -> None:
    file_name = "Drone_paths.txt"
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
        print(f" ParserError: {e}")
