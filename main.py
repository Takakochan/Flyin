from find_path import CBSSolver
from parser import parser, select_file, ParserError


def main():
    print("Hello from flyin!")
    file = select_file()
    graph = parser(file)
    print(graph)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    try:
        solver.solve()
    except RuntimeError:
        solver.solve2()


if __name__ == "__main__":
    try:
        main()
    except (ParserError, ValueError) as e:
        print(f" ParserError: {e}")
