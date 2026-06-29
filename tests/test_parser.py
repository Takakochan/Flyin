from parser import parser


def test_linear_map():
    graph = parser("maps/easy/01_linear_path.txt")

    assert graph.nb_drone == 5
    assert len(graph.zones) == 4
    assert len(graph.connections) == 3