import heapq
from itertools import count
from dataclasses import dataclass
import math
from collections import defaultdict, deque

from graph import Graph
from zone import Zone, Position, ZoneType
from parser import select_file, parser
from draw_map import PlotlyVisualizer


@dataclass(frozen=True)
class Constraint():
    dron_id: int
    zone_name: str
    time_step: int


@dataclass(frozen=True)
class Conflict():
    dron_id_a: int
    dron_id_b: int
    zone_name: str
    time_step: int


@dataclass
class CTNode:
    constraints: frozenset[Constraint]
    paths: dict[int, list[str]]

    @property
    def cost(self) -> float:
        return sum(len(p) for p in self.paths.values())

    def __lt__(self, other: "CTNode") -> bool:
        return self.cost < other.cost


class CBSSolver():
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def solve(self):
        start_zone = next(z for z in self.graph.zones.values()
                          if z.zone_role == "start")
        goal_zone = next(z for z in self.graph.zones.values()
                         if z.zone_role == "end")
        h_step_scores = h_step_score(self.graph, goal_zone)
        root_paths = {
            d: a_star(self.graph, start_zone,
                      goal_zone, frozenset(), d, h_score)
            for d in range(self.graph.nb_drone)
        }
        root = CTNode(frozenset(), root_paths)
        open_list = [root]
        visited_nodes: set[frozenset] = set()
        iteration = 0

        while open_list:
            node = heapq.heappop(open_list)
            if node.constraint in visited_nodes:
                continue
            visited_nodes.add(node.constraints)
            iteration += 1
            if iteration > 15000:
                raise RuntimeError("CBS timeout")
            occupance_table = self._set_occupance_table(node.paths)
            conflict = self.conflict_detector(occupance_table)
            if conflict is None:
                PlotlyVisualizer.draw(self.graph, node.paths)
                return node.paths

            for drone_id in (conflict.dron_id_a, conflict.dron_id_b):
                new_constraints = node.constraints | {
                    Constraint(drone_id,
                               conflict.zone_name,
                               conflict.time_step,)
                }
                new_path = a_star(self.graph, start_zone, goal_zone,
                                  new_constraints, drone_id, h_step_scores)
                if new_path:
                    new_path = {**node.paths, drone_id: new_path}
                    child = CTNode(new_constraints, new_path)
                    heapq.heappush(open_list, child)

    def _set_occupance_table(self, paths: dict) -> dict:
        """
        occupance_table = dict [tuple[zone_name, time_step], list[drone_id]]
        """
        self.occupance_table = defaultdict(list)
        for drone_id, path in paths.items():
            for time_step, zone_name in enumerate(path):
                self.occupance_table[(zone_name, time_step)].append(drone_id)
        return dict(self.occupance_table)
        # TO_DO check the type between returnt with dict() or bear

    def conflict_detector(self, occupance_table: dict) -> Conflict | None:
        for (zone_name, time_step), dron_ids in occupance_table.items():
            if time_step == 0:
                continue
            zone = self.graph.zones[zone_name]
            if zone.zone_role in ('start', 'end'):
                continue
            max_drones = self.graph.zones[zone_name].max_drones
            if max_drones < len(dron_ids):
                return Conflict(dron_ids[0], dron_ids[1], zone_name, time_step)
        return None

    def constraint_generator(self, conflict) -> set[Constraint]:
        constraint_b = Constraint(
            conflict.dron_id_b,
            conflict.zone_name,
            conflict.time_step)
        return {constraint_b}


def a_star(
    graph: Graph,
    start: Zone,
    goal: Zone,
    constraints: set[Constraint],
    drone_id: int,
    h_step_scores: dict[str, int]
) -> list[str]:

    time_step: int = 0
    path: list[str] = []
    neighbours = []
    came_from: dict[tuple[str, int], tuple[str, int]] = {}
    constraint_set = {(c.zone_name, c.time_step) for c in constraints
                      if c.dron_id == drone_id}
    visited_set: set[tuple[str, int]] = set()
    open_queue = PriorityQueue()
    open_queue.push(h_step_scores.get(start.name, len(graph.zones)),
                    start, time_step)

    while not open_queue.is_empty():
        current, time_step = open_queue.pop()
        if current == goal:
            break
        current_set = (current.name, time_step)
        neighbours = graph.adjacency.get(current.name, [])
        for next_zone_name in neighbours:
            next_zone = graph.zones[next_zone_name]
            if next_zone.zone_type == ZoneType.BLOCKED:
                continue
            next_time_step = time_step + 1
            conn = graph.connections.get((current.name, next_zone_name))
            restricted = 1 if conn and conn.extra_step else 0
            priority = -0.1 if next_zone.zone_type == ZoneType.PRIORITY else 0
            extra_time = next_time_step + restricted
            new_state = (next_zone_name, next_time_step)
            if new_state in constraint_set:
                continue
            if new_state in visited_set:
                continue
            visited_set.add(new_state)
            came_from[new_state] = current_set
            next_zone = graph.zones[next_zone_name]
            next_f = next_time_step + h_step_scores.get(next_zone_name, 999) + extra_time + priority
            open_queue.push(next_f, next_zone, next_time_step)
        max_t = len(graph.zones) * graph.nb_drone * 3
        if time_step + 1 < max_t:
            wait_state = (current.name, time_step + 1)
            if neighbours and wait_state not in constraint_set and wait_state not in visited_set:
                visited_set.add(wait_state)
                came_from[wait_state] = current_set
                wait_f = (time_step + 1) + h_step_scores.get(current.name,  len(graph.zones))
                open_queue.push(wait_f, current, time_step + 1)
        if current != goal:
            return []

    current_state = (goal.name, time_step)
    while current_state in came_from:
        path.append(current_state[0])
        current_state = came_from[current_state]
    path.append(start.name)
    path.reverse()
    return path


def h_step_score(graph: Graph, goal: Zone) -> dict[str, int]:
    dist = {goal.name: 0}
    queue = deque([goal.name])
    reverse_adj: dict[str, list[str]] = {}
    for origin, neighbors in graph.adjacency.items():
        for num in neighbors:
            reverse_adj.setdefault(num, []).append(origin)
    while queue:
        current = queue.popleft()
        for prev in reverse_adj.get(current, []):
            if prev not in dist:
                dist[prev] = dist[current] + 1
                queue.append(prev)
    return dist


def h_score(zone: Position, goal: Position) -> float:
    return math.sqrt((goal.x - zone.x)**2 + (goal.y - zone.y)**2)


class PriorityQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Zone, int]] = []
        self._counter = count()

    def push(self, f_score: float, zone: Zone, time_step: int) -> None:
        heapq.heappush(self._heap,
                       (f_score, next(self._counter), zone, time_step))

    def pop(self) -> tuple[Zone, int]:
        f_score, _, zone, time_step = heapq.heappop(self._heap)
        return (zone, time_step)

    def is_empty(self) -> bool:
        return len(self._heap) == 0


if __name__ == '__main__':
    file = select_file()
    graph = parser(file)
    PlotlyVisualizer.draw(graph)
    solver = CBSSolver(graph)
    solver.solve()
