import plotly.graph_objects as go

from graph import Graph
from zone import ZoneType
from time_line import TimeLine


class PlotlyVisualizer:
    @staticmethod
    def draw(graph: Graph, tl: TimeLine) -> None:
        fig = go.Figure()
        edge_x = []
        edge_y = []
        edge_hover = []
        for _, connection in graph.connections.items():
            origin = graph.zones[connection.origin]
            to = graph.zones[connection.to]
            edge_x.extend(
                [
                    origin.position.x,
                    to.position.x,
                    None,
                ]
            )
            edge_y.extend(
                [
                    origin.position.y,
                    to.position.y,
                    None,
                ]
            )
            text = f"max_link_capacity: {connection.max_link_capacity}"
            edge_hover.extend([text, text, None])
        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                opacity=0.3,
                line=dict(color="gray"),
                hovertext=edge_hover,
                hoverinfo="text",
            )
        )
        mid_x = []
        mid_y = []
        mid_hover = []
        edges = []
        for name, connection in graph.connections.items():
            origin = graph.zones[connection.origin]
            to = graph.zones[connection.to]
            mid_x.append((origin.position.x + to.position.x) / 2)
            mid_y.append((origin.position.y + to.position.y) / 2)
            mid_hover.append(f"max_link_capacity: "
                             f"{connection.max_link_capacity}")
            edges.append(name)

        fig.add_trace(
            go.Scatter(
                x=mid_x,
                y=mid_y,
                mode="markers",
                marker=dict(size=80, color="gray", opacity=0.01),
                hovertext=mid_hover,
                hoverinfo="text",
                showlegend=False,
            )
        )
        for zone in graph.zones.values():
            if zone.color == "rainbow":
                colors = [
                    "red",
                    "orange",
                    "yellow",
                    "green",
                    "blue",
                    "indigo",
                    "purple",
                ]
                sizes: list[int] = [80, 70, 60, 50, 40, 30, 20]
                z_names = [zone.name, None, None, None, None, None, None]
                for size, color, z_name in zip(sizes, colors, z_names):
                    fig.add_trace(
                        go.Scatter(
                            x=[zone.position.x],
                            y=[zone.position.y],
                            mode="markers + text",
                            marker=dict(size=size, color=color),
                            showlegend=False,
                            textposition="top center",
                            texttemplate=z_name,
                            hovertext=(f"{zone.name}<br>max_drones: "
                                       f"{zone.max_drones}"),
                            hoverinfo="text",
                        )
                    )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=[zone.position.x],
                        y=[zone.position.y],
                        mode="markers+text",
                        opacity=0.7,
                        marker=dict(size=60, color=zone.color),  # ← ここ重要
                        textposition="top center",
                        text=zone.name,
                        textfont=dict(size=10, color="blue"),
                        showlegend=False,
                        hovertext=(
                            f"max_drones: {zone.max_drones}"
                            f"<br>zone_type: {zone.zone_type}"
                        ),
                        hoverinfo="text",
                    )
                )

        drone_trace_idx = len(fig.data)
        max_t = len(tl.turns)

        """
        Dysplay for drones
        """

        def _drone_scatter(t: int) -> go.Scatter:
            x, y, hover, labels, zone_names = [], [], [], [], []
            for event in sorted(tl.turns[t], key=lambda e: e.drone):
                drone_id = event.drone
                state = tl.get_state(t, drone_id)
                zone_name = state.location
                if state.status == "connection":
                    zone_name = zone_name[zone_name.find("-") + 1:]
                zone = graph.zones[zone_name]
                if zone.zone_type == ZoneType.RESTRICTED:
                    if t > 0:
                        prev_state = tl.get_state(t - 1, drone_id)
                        prev_name = prev_state.location
                        if prev_state.status == "connection":
                            prev_name = prev_name[prev_name.find("-") + 1:]
                    else:
                        prev_name = zone_name

                    previous_zone = graph.zones[prev_name]
                    x.append((zone.position.x + previous_zone.position.x) / 2)
                    y.append((zone.position.y + previous_zone.position.y) / 2)
                    # zone_name = f"{previous_zone.name}-{zone.name}"
                else:
                    x.append(zone.position.x)
                    y.append(zone.position.y)
                hover.append(f"Drone {drone_id + 1}<br>Zone: {zone_name}<br>t={t}")
                labels.append(f"D{drone_id + 1}")
                zone_names.append(zone_name)

            if t >= 1:
                output_parts = []
                for event in sorted(tl.turns[t], key=lambda e: e.drone):
                    drone_id = event.drone
                    curr = tl.get_state(t, drone_id).location
                    prev = tl.get_state(t - 1, drone_id).location
                    if curr == prev:
                        continue

                    output_parts.append(f"D{drone_id + 1}-{curr}")
                file_name = "Dron_paths.txt"
                if output_parts:
                    with open(file_name, "a", encoding="utf-8") as file:
                        file.write(" ".join(output_parts) + "\n")
            return go.Scatter(
                x=x,
                y=y,
                mode="markers+text",
                marker=dict(size=30, color="red", symbol="cross"),
                text=labels,
                textfont=dict(color="white", size=15),
                textposition="middle center",
                hovertext=hover,
                hoverinfo="text",
                name="drones",
                showlegend=False,
            )

        fig.add_trace(_drone_scatter(0))
        fig.frames = [
            go.Frame(data=[_drone_scatter(t)],
                     name=str(t),
                     traces=[drone_trace_idx])
            for t in range(max_t)
        ]

        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    showactive=False,
                    buttons=[
                        dict(
                            label="Play",
                            method="animate",
                            args=[
                                None,
                                {
                                    "frame": {"duration": 600, "redraw": True},
                                    "fromcurrent": True,
                                },
                            ],
                        ),
                        dict(
                            label="Pause",
                            method="animate",
                            args=[
                                [None],
                                {
                                    "frame": {"duration": 0, "redraw": False},
                                    "mode": "immediate",
                                },
                            ],
                        ),
                    ],
                )
            ],
            sliders=[
                dict(
                    steps=[
                        dict(
                            method="animate",
                            args=[
                                [str(t)],
                                {
                                    "frame": {"duration": 0, "redraw": True},
                                    "mode": "immediate",
                                },
                            ],
                            label=str(t),
                        )
                        for t in range(max_t)
                    ],
                    currentvalue=dict(prefix="t = "),
                )
            ],
        )
        fig.show()
