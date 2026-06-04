from typing import Protocol
import heapq
from itertools import count
from dataclasses import dataclass

from graph import Graph
from zone import Zone
from connection import Connection
from draw_map import DrawConnection



@dataclass
class Constraint():
    dron_id: int
    zone_name: str
    time_step: int


@dataclass
class Conflict():
    dron_id_a: int
    dron_id_b: int
    zone_name: str
    time_step: int



class CBSSolver():
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
    def solve() -> Path:
        ...


def a_star(
    self,
    graph: Graph,
    start: Zone,
    goal: Zone,
    constraints: set[constraint],
) -> list[str]:

    time_step: int = 0
    path: list[str] = []
    neighbours = []

    open_queue = PriorityQueue()
    open_queue.push(time_step, start)

    while not open_queue.is_empty():
        current = open_queue.pop()
        if current is None:
            break
        if current == goal:
            break

        neighbours = graph.adjacency[current.name]
        current_g = g_score(current.name)


    return list[]


def g_score()


class PriorityQueue:
    def __init__(self, dest: Zone) -> None:
        self._heap: list[tuple[int, int, Zone]] = []
        self._counter = count()
        self._dest = dest

    def push(self, f_score: int, zone: Zone) -> None:
        heapq.heappush(self._heap,
                       f_score, next(self._counter), zone)

    def pop(self) -> Zone:
        return heapq.heappop(self._heap)[2]


    def is_empty(self) -> bool:
        return len(self._heap) == 0
