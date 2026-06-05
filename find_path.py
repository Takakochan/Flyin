import heapq
from itertools import count
from dataclasses import dataclass
import math

from graph import Graph
from zone import Zone, Position


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
    constraints: set[Constraint],
) -> list[str]:

    time_step: int = 0
    path: list[str] = []
    neighbours = []
    came_from: dict[tuple[str, int], tuple[str, int]] = {}
    constraint_set = {(c.zone_name, c.time_step) for c in constraints}
    visited_set: set[tuple[str, int]] = set()
    open_queue = PriorityQueue(goal, time_step)
    open_queue.push(h_score(start.position, goal.position), start, time_step)

    while not open_queue.is_empty():
        current, time_step = open_queue.pop()
        if current is None:
            break
        if current == goal:
            break

        current_set = (current.name, time_step)
        neighbours = graph.adjacency[current.name]
        for next_zone_name in neighbours:
            next_time_step = time_step + 1
            new_set = (next_zone_name, next_time_step)
            if new_set in constraint_set:
                continue
            if new_set in visited_set:
                continue
            visited_set.add(new_set)
            came_from[new_set] = current_set
            next_zone = graph.zones[next_zone_name]
            next_f = next_time_step + h_score(next_zone.position, goal.position)
            open_queue.push(next_f, next_zone, next_time_step)

        current_state = (goal.name, time_step) #recover to current state
        while current_state in came_from:
            path.append(current_state[0])
            current_state = came_from[current_state]
        path.append(start.name)
        path.reverse()
    return path


def h_score(zone: Position, goal: Position) -> float:
    return math.sqrt((goal.x - zone.x)**2 + (goal.y - zone.y)**2)



class PriorityQueue:
    def __init__(self, dest: Zone, time_step: int) -> None:
        self._heap: list[tuple[int, int, Zone, int]] = []
        self._counter = count()
        self._dest = dest

    def push(self, f_score: float, zone: Zone, time_step: int) -> None:
        heapq.heappush(self._heap,
                       f_score,
                       zone,
                       time_step)

    def pop(self) -> tuple[Zone, int]:
        f_score, _, zone, time_step = heapq.heappop(self._heap)
        return (zone, time_step)


    def is_empty(self) -> bool:
        return len(self._heap) == 0
