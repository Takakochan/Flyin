<<<<<<< HEAD
from find_path import CBSSolver
from parser import parser, select_file, ParserError


def main():
    print("Hello from flyin!")
=======
from parser import select_file, parser, ParserError
from find_path import CBSSolver


def main():
>>>>>>> 3b2c00bf9770a154cca12ac03b61bfc062d3107c
    file = select_file()
    graph = parser(file)
    print(graph)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    try:
<<<<<<< HEAD
        solver.solve()
=======
        solver.solve2()
>>>>>>> 3b2c00bf9770a154cca12ac03b61bfc062d3107c
    except RuntimeError:
        solver.solve2()


if __name__ == "__main__":
    try:
        main()
    except (ParserError, ValueError) as e:
<<<<<<< HEAD
        print(f" ParserError: {e}")
=======
        print(e)
>>>>>>> 3b2c00bf9770a154cca12ac03b61bfc062d3107c
