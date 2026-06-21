import plotly.express as px
import pandas as pd

from parser import parser, select_file
from draw_map import PlotlyVisualizer
from find_path import CBSSolver


def make_df(paths: dict):
    data_list = paths.values()
    df = pd.DataFrame(data_list)
    print(df)
    # fig = px.line(df, y=df.columns)
    # fig.show()


if __name__ == "__main__":
    file = select_file()
    graph = parser(file)
    print(graph)
    PlotlyVisualizer.draw(graph)
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    paths = solver.solve()
    make_df(paths)
