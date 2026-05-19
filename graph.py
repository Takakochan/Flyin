from zone import Zone
from connection import Connection
from pydantic import BaseModel

class Graph(BaseModel):
	zones: dict[str, Zone]
	connections: list[Connection]


	def get_neighbors(self, zone_name)