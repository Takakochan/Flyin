import heapq
from itertools import count
from dataclasses import dataclass
import math

from parser import parser, select_file
from graph import Graph
from zone import Zone, Position
from connection import Connection
from draw_map import DrawConnection


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


class CBSSolver():
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def solve(self) -> list[str]:
        paths: dict[int, list] = {}
        start_zone = next(z for z in self.graph.zones.values() if z.zone_role == "start")
        goal_zone = next(z for z in self.graph.zones.values() if z.zone_role == 'end')
        constraints: set[Constraint] = set()
        for drone_id in range(self.graph.nb_drone):
            print(f"DEBUG:: dorone_id::{drone_id}")
            path = a_star(self.graph, start_zone, goal_zone, constraints, drone_id)
            paths[drone_id] = path

        while True:
            conflict = self.conflict_detector(paths)
            print(conflict)
            print(paths)
            if conflict is None:
                return paths
            constraint = self.constraint_generator(conflict)
            for c in constraint:
                constraints.add(c)
            for drone_id in range(self.graph.nb_drone):
                paths[drone_id] = a_star(self.graph, start_zone, goal_zone, constraints, drone_id)


    def conflict_detector(self, paths) -> Conflict:
        for drone_id in range(len(paths) - 1):
            path_a = paths[drone_id]
            path_b = paths[drone_id + 1]
            for time_step, (zone_a, zone_b) in enumerate(zip(path_a, path_b)):
                if zone_a == zone_b and time_step != 0: #zone.max_drones
                    conflict = Conflict(drone_id, drone_id + 1, zone_a, time_step)
                    return conflict
        return None


    def constraint_generator(self, conflict) -> set[Constraint]:
        constraint_a = Constraint(conflict.dron_id_a, conflict.zone_name, conflict.time_step)
        constraint_b = Constraint(conflict.dron_id_b, conflict.zone_name, conflict.time_step)
        return (constraint_a, constraint_b)


def a_star(
    graph: Graph,
    start: Zone,
    goal: Zone,
    constraints: set[Constraint],
    drone_id: int
) -> list[str]:

    time_step: int = 0
    path: list[str] = []
    came_from: dict[tuple[str, int], tuple[str, int]] = {} #dict[tuple current, tuple previous]
    neighbours = []
    visited_set: set[tuple[str, int]] = set()
    constraint_set = {(c.zone_name, c.time_step) for c in constraints if c.dron_id == drone_id} #制約のあるzoneとタイムステップの記録
    open_queue = PriorityQueue()
    open_queue.push(h_score(start.position, goal.position), start, time_step)

    while not open_queue.is_empty():
        current, time_step = open_queue.pop()
        if current == goal:
            break
        # print(f"Zone name {current.name}")
        current_set = (current.name, time_step)
        neighbours = graph.adjacency.get(current.name, []) #Neighbours which are connected from current zone
        # if neighbours is None:
        #     print(f"Neigbours: {neighbours}")
        #     continue
        for next_zone_name in neighbours:
            next_time_step = time_step + 1
            new_state = (next_zone_name, next_time_step)
            if new_state in constraint_set:
                continue
            if new_state in visited_set:
                continue
            visited_set.add(new_state)
            came_from[new_state] = current_set
            next_zone = graph.zones[next_zone_name]
            next_f = next_time_step + h_score(next_zone.position, goal.position)
            open_queue.push(next_f, next_zone, next_time_step)

        #2. 経路の復元 — ループを抜けた後、came_from を逆向きにたどって path を作る処理がまだありません。
    current_state = (goal.name, time_step)
    while current_state in came_from:
        path.append(current_state[0])
        current_state = came_from[current_state]
    path.append(start.name)
    path.reverse()
    return path


def h_score(n: Position, goal: Position) -> float:
    return math.sqrt((goal.x - n.x)**2 + (goal.y - n.y)**2) # ピタゴラスの定理

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
    print(f"Number of Drone: {graph.nb_drone}")
    solver = CBSSolver(graph)
    solver.solve()
    #start_zone = next(z for z in graph.zones.values() if z.zone_role == "start")
    #goal_zone = next(z for z in graph.zones.values() if z.zone_role == 'end')
    #constraints: set[Constraint] = set()
    #path = a_star(graph, start_zone, goal_zone, constraints)

    # print(path)
