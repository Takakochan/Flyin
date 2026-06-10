# %%
import matplotlib.pyplot as plt
from graph import Graph


class DrawConnection():
    @staticmethod
    def draw(graph: Graph) -> None:
        w_px, h_px = 1800, 800
        dpi = 80
        fig, ax = plt.subplots(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
        for i, connection in enumerate(graph.connections):
            origin = graph.zones[connection.origin]
            to = graph.zones[connection.to]
            plt.plot([origin.position.x, to.position.x], [origin.position.y, to.position.y], color='gray')
        for zone in graph.zones.values():
            if zone.color == 'rainbow':
                plt.plot(zone.position.x, zone.position.y, color='red', marker='o', markersize=80)
                plt.plot(zone.position.x, zone.position.y, color='yellow', marker='o', markersize=64)
                plt.plot(zone.position.x, zone.position.y, color='green', marker='o', markersize=40)
                plt.plot(zone.position.x, zone.position.y, color='blue', marker='o', markersize=20)
                plt.text(zone.position.x, zone.position.y, zone.name, color='white',ha="center", va="center", fontsize=8)
            else:
                plt.plot(zone.position.x, zone.position.y, color=zone.color, marker='o', markersize=60)
                plt.text(zone.position.x, zone.position.y, zone.name, color='white', ha="center", va="center", fontsize=8)
        plt.show()