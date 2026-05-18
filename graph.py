from zone import Zone
from connection import Connection

class Graph:
	zones: dict[str, Zone]
	connections: list[Connection]


	def get_neighbors(self, zone_name)