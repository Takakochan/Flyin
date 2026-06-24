from find_path import CBSSolver
from parser import parser, select_file, ParserError


def main() -> None:
    format_txt_file()
    file = select_file()
    graph = parser(file)
    # print(graph)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    try:
        solver.solve()
    except RuntimeError:
        solver.solve2()


def format_txt_file() -> None:
    file_name = "Dron_paths.txt"
    with open(file_name, "w", encoding="utf-8") as _:
        pass


if __name__ == "__main__":
    try:
        main()
    except (ParserError, ValueError) as e:
        print(f" ParserError: {e}")
