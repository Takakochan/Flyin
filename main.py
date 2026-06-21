from parser import select_file, parser, ParserError
from find_path import CBSSolver


def main():
    file = select_file()
    graph = parser(file)
    print(graph)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    try:
        solver.solve2()
    except RuntimeError:
        solver.solve2()


if __name__ == "__main__":
    try:
        main()
    except (ParserError, ValueError) as e:
        print(e)