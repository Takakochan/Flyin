# %%
# import matplotlib.pyplot as plt
from graph import Graph
import plotly.graph_objects as go


# class DrawConnection():
#     @staticmethod
#     def draw(graph: Graph) -> None:
#         w_px, h_px = 3600, 1600
#         dpi = 80
#         fig, ax = plt.subplots(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
#         for i, connection in enumerate(graph.connections):
#             origin = graph.zones[connection.origin]
#             to = graph.zones[connection.to]
#             plt.plot([origin.position.x, to.position.x], [origin.position.y, to.position.y], color='gray')
#         for zone in graph.zones.values():
#             if zone.color == 'rainbow':
#                 plt.plot(zone.position.x, zone.position.y, color='red', marker='o', markersize=80)
#                 plt.plot(zone.position.x, zone.position.y, color='yellow', marker='o', markersize=64)
#                 plt.plot(zone.position.x, zone.position.y, color='green', marker='o', markersize=40)
#                 plt.plot(zone.position.x, zone.position.y, color='blue', marker='o', markersize=20)
#                 plt.text(zone.position.x, zone.position.y, zone.name, color='white',ha="center", va="center", fontsize=8)
#             else:
#                 plt.plot(zone.position.x, zone.position.y, color=zone.color, marker='o', markersize=60)
#                 plt.text(zone.position.x, zone.position.y, zone.name, color='white', ha="center", va="center", fontsize=8)
#         plt.show()


class PlotlyVisualizer():
    @staticmethod
    def draw(graph: Graph) -> None:
        fig = go.Figure()
        edge_x = []
        edge_y = []
        edge_hover = []

        for name_to, connection in graph.connections.items():
            origin = graph.zones[connection.origin]
            to = graph.zones[connection.to]
            edge_x.extend([
                origin.position.x,
                to.position.x,
                None,
            ])
            edge_y.extend([
                origin.position.y,
                to.position.y,
                None,
            ])
            text = f"max_link_capacity: {connection.max_link_capacity}"
            edge_hover.extend([text, text, None])
        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                opacity=.5,
                line=dict(color="gray"),
                hovertext=edge_hover,
                hoverinfo="text",
            )
        )

        mid_x = []
        mid_y = []
        mid_hover = []
        for _, connection in graph.connections.items():
            origin = graph.zones[connection.origin]
            to = graph.zones[connection.to]
            mid_x.append((origin.position.x + to.position.x) / 2)
            mid_y.append((origin.position.y + to.position.y) / 2)
            mid_hover.append(f"max_link_capacity:　{connection.max_link_capacity}")

        fig.add_trace(go.Scatter(
            x=mid_x,
            y=mid_y,
            mode="markers",
            marker=dict(size=80, color="gray", opacity=0.01),
            hovertext=mid_hover,
            hoverinfo="text",
            showlegend=False,
        ))
        sizes = [
            (80, "red"),
            (64, "yellow"),
            (40, "green"),
            (20, "blue"),
        ]
        for zone in graph.zones.values():
            if zone.color == "rainbow":
                colors = ["red", "yellow", "green", "blue"]
                sizes = [80, 64, 40, 20]
                for size, color in zip(sizes, colors):
                    fig.add_trace(
                        go.Scatter(
                            x=[zone.position.x],
                            y=[zone.position.y],
                            mode="markers",
                            opacity=.5,
                            marker=dict(size=size, color=color),
                            showlegend=False,
                            hovertext=f"{zone.name}<br>max_drones: {zone.max_drones}",
                            hoverinfo="text",
                        )
                    )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=[zone.position.x],
                        y=[zone.position.y],
                        mode="markers",
                        opacity=.7,
                        marker=dict(size=60, color=zone.color),  # ← ここ重要
                        showlegend=False,
                        hovertext=f"{zone.name}<br>max_drones: {zone.max_drones}",
                        hoverinfo="text",
                    )
                )
        fig.show()
