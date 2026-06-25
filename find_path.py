import heapq
from collections import deque
from itertools import count
from dataclasses import dataclass


from parser import parser, select_file
from graph import Graph
from zone import Zone, ZoneType
from draw_map import PlotlyVisualizer


@dataclass(frozen=True)
class Constraint:
    dron_id: int
    zone_name: str
    time_step: int


@dataclass(frozen=True)
class Conflict:
    dron_id_a: int
    dron_id_b: int
    zone_name: str
    time_step: int


class PathError(Exception):
    pass


@dataclass
class PathNotFoundError(PathError):
    def __str__(self) -> str:
        return "Path was not found"


@dataclass
class CTNode:
    constraints: frozenset[Constraint]
    paths: dict[int, list[str]]

    @property
    def cost(self) -> float:
        return sum(len(p) for p in self.paths.values())

    def __lt__(self, other: "CTNode") -> bool:
        return self.cost < other.cost


type Path = list[str]
type Paths = dict[int, Path]


class CBSSolver:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def solve(self) -> Paths | None:
        start_zone = next(
            z for z in self.graph.zones.values() if z.zone_role == "start"
        )
        goal_zone = next(
            z for z in self.graph.zones.values() if z.zone_role == "end"
        )
        h_scores = h_step_score(self.graph, goal_zone)
        root_paths = {
            d: a_star(self.graph, start_zone,
                      goal_zone, frozenset(), d, h_scores)
            for d in range(self.graph.nb_drone)
        }
        root = CTNode(frozenset(), root_paths)
        open_list = [root]
        visited_nodes: set[frozenset[Constraint]] = set()
        iteration = 0
        while open_list:
            node = heapq.heappop(open_list)  # 最小コストを展開
            if node.constraints in visited_nodes:
                continue
            visited_nodes.add(node.constraints)
            iteration += 1
            if iteration > 10000:
                raise RuntimeError("CBS timeout")
            occupance_table = self._set_occupance_table(node.paths)
            conflict = self.conflict_detector(occupance_table)
            if conflict is None:
                print(f"finished at iter={iteration}")
                PlotlyVisualizer.draw(self.graph, node.paths)
                return node.paths  # 衝突なし → 解
            # 2つの子ノードを生成
            for drone_id in (conflict.dron_id_a, conflict.dron_id_b):
                new_constraints = frozenset(node.constraints | {
                    Constraint(drone_id,
                               conflict.zone_name,
                               conflict.time_step)
                })
                """
                | は **集合(set)や型の「和(union」**を表している記号
                """
                new_path = a_star(
                    self.graph,
                    start_zone,
                    goal_zone,
                    new_constraints,
                    drone_id,
                    h_scores,
                )
                if new_path:
                    new_paths = {**node.paths, drone_id: new_path}
                    child = CTNode(new_constraints, new_paths)
                    heapq.heappush(open_list, child)
        return None

    def solve2(self) -> Paths:
        paths: dict[int, list[str]] = {}
        start_zone = next(
            z for z in self.graph.zones.values() if z.zone_role == "start"
        )
        goal_zone = next(
            z for z in self.graph.zones.values() if z.zone_role == "end"
        )
        h_scores = h_step_score(self.graph, goal_zone)
        for drone_id in range(self.graph.nb_drone):
            occupancy = self._set_occupance_table(paths)
            constraints: set[Constraint] = set()
            for (zone_name, t), occupants in occupancy.items():
                zone = self.graph.zones.get(zone_name)
                if zone is None or zone.zone_role in ("start", "end"):
                    continue
                if len(occupants) >= zone.max_drones:
                    constraints.add(Constraint(drone_id, zone_name, t))
            path = a_star(
                self.graph, start_zone, goal_zone,
                frozenset(constraints), drone_id, h_scores
            )
            if not path:
                raise ValueError(f"No path for drone {drone_id}")
            paths[drone_id] = path
        PlotlyVisualizer.draw(self.graph, paths)
        return paths

    def _set_occupance_table(
            self,
            paths: dict[int, list[str]]
    ) -> dict[tuple[str, int], list[int]]:
        """
        各 (ゾーン, 時刻) に居るドローンを記録する。衝突検出に使う。
        """
        occupance_table: dict[tuple[str, int], list[int]] = {}
        for drone_id, path in paths.items():
            for time_step, p in enumerate(path):
                if "-" in p:
                    continue
                new_set = (p, time_step)
                if new_set in occupance_table:
                    occupance_table[new_set].append(drone_id)
                else:
                    occupance_table[new_set] = [drone_id]
        return occupance_table

    def conflict_detector(
            self,
            occupance_table: dict[tuple[str, int], list[int]]
    ) -> Conflict | None:
        for (zone_name, time_step), dron_ids in occupance_table.items():
            if time_step == 0:
                continue
            zone = self.graph.zones[zone_name]
            if zone is None:
                continue
            if zone.zone_role in ("start", "end"):
                continue
            max_drons = self.graph.zones[zone_name].max_drones
            if max_drons < len(dron_ids):
                return Conflict(dron_ids[0], dron_ids[1], zone_name, time_step)
        return None

    def constraint_generator(self, conflict: Conflict) -> set[Constraint]:

        constraint_b = Constraint(
            conflict.dron_id_b, conflict.zone_name, conflict.time_step
        )
        return {constraint_b}


def a_star(
    graph: Graph,
    start: Zone,
    goal: Zone,
    constraints: frozenset[Constraint],
    drone_id: int,
    h_scores: dict[str, int],
) -> list[str]:

    time_step: int = 0
    path: list[str] = []
    came_from: dict[
        tuple[str, int], tuple[str, int]
    ] = {}  # dict[tuple current, tuple previous]
    neighbours = []
    visited_set: set[tuple[str, int]] = set()
    constraint_set = {
        (c.zone_name, c.time_step)
        for c in constraints if c.dron_id == drone_id
    }  # 制約のあるzoneとタイムステップの記録
    open_queue = PriorityQueue()
    open_queue.push(h_scores.get(start.name, len(graph.zones)),
                    start, time_step)
    while not open_queue.is_empty():
        if time_step >= len(graph.zones) * 2:
            raise PathNotFoundError()
        current, time_step = open_queue.pop()
        if current == goal:
            break
        current_set = (current.name, time_step)
        neighbours = graph.adjacency.get(current.name, [])
        # Neighbours which are connected from current zone
        for next_zone_name in neighbours:
            next_zone = graph.zones[next_zone_name]
            if next_zone.zone_type == ZoneType._BLOCKED:
                continue
            next_time_step = time_step + 1
            conn = graph.connections.get((current.name, next_zone_name))
            restrict = 1 if conn and conn.extra_step else 0
            priority = -0.1 if next_zone.zone_type == ZoneType.PRIORITY else 0
            extra_time = next_time_step + restrict
            new_state = (next_zone_name, extra_time)
            if new_state in constraint_set:
                continue
            if new_state in visited_set:
                continue
            visited_set.add(new_state)
            came_from[new_state] = current_set

            next_f = sum([
                next_time_step, h_scores.get(next_zone_name, 999),
                restrict, priority]
            )
            open_queue.push(next_f, next_zone, extra_time)
        max_t = len(graph.zones) * graph.nb_drone * 3
        if time_step + 1 < max_t:
            wait_state = (current.name, time_step + 1)
            if (
                neighbours and wait_state
                not in constraint_set and wait_state not in visited_set
            ):
                visited_set.add(wait_state)
                came_from[wait_state] = current_set
                wait_f = (time_step + 1) + h_scores.get(
                    current.name, len(graph.zones)
                )
                open_queue.push(wait_f, current, time_step + 1)
    if current != goal:
        return []
        # 2. 経路の復元 — ループを抜けた後、came_from を逆向きにたどって path を作る。
    current_state = (goal.name, time_step)
    while current_state in came_from:
        current_state_name, _ = current_state

        zone = graph.zones[current_state_name]
        if zone.zone_type == ZoneType.RESTRICTED:
            pre = path[-1]
            if "-" in pre:
                pre = pre[: pre.rfind("-")]
            extra = f"{pre}-{current_state[0]}"
            path.append(current_state[0])
            path.append(extra)
            current_state = came_from[current_state]

        else:
            path.append(current_state[0])
            current_state = came_from[current_state]
    path.append(start.name)
    path.reverse()
    return path


def h_step_score(graph: Graph, goal: Zone) -> dict[str, int]:
    dist = {goal.name: 0}
    queue = deque([goal.name])
    reverse_adj: dict[str, list[str]] = {}
    for origin, neigbours in graph.adjacency.items():
        for num in neigbours:
            reverse_adj.setdefault(num, []).append(origin)
    while queue:
        current = queue.popleft()
        for prev in reverse_adj.get(current, []):
            if prev not in dist:
                dist[prev] = dist[current] + 1
                queue.append(prev)
    return dist


class PriorityQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Zone, int]] = []
        self._counter = count()

    def push(self, f_score: float, zone: Zone, time_step: int) -> None:
        heapq.heappush(
            self._heap,
            (f_score,
             next(self._counter),
             zone,
             time_step)
        )

    def pop(self) -> tuple[Zone, int]:
        f_score, _, zone, time_step = heapq.heappop(self._heap)
        return (zone, time_step)

    def is_empty(self) -> bool:
        return len(self._heap) == 0


if __name__ == "__main__":
    file = select_file()
    graph = parser(file)
    solver = CBSSolver(graph)
    try:
        solver.solve()
    except RuntimeError:
        solver.solve2()
