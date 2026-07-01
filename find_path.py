import heapq
import time
from collections import deque
from itertools import count
from dataclasses import dataclass


from parser import parser, select_file
from graph import Graph
from zone import Zone, ZoneType
from draw_map import PlotlyVisualizer
from time_line import TimeLine, MoveEvent


@dataclass(frozen=True)
class Constraint:
    """A prohibition forbidding one drone from occupying a zone at a time.

    Attributes:
        dron_id: Identifier of the drone the constraint applies to.
        zone_name: Name of the forbidden zone.
        time_step: Time step at which the zone is forbidden.
    """
    dron_id: int
    zone_name: str
    time_step: int


@dataclass(frozen=True)
class Conflict:
    """Two drones occupying the same over-capacity zone at the same time.

    Attributes:
        dron_id_a: Identifier of the first conflicting drone.
        dron_id_b: Identifier of the second conflicting drone.
        zone_name: Name of the contested zone (or connection endpoint).
        time_step: Time step at which the conflict occurs.
    """
    dron_id_a: int
    dron_id_b: int
    zone_name: str
    time_step: int


class PathError(Exception):
    """Base class for path-finding errors."""
    pass


@dataclass
class PathNotFoundError(PathError):
    """Raised when A* cannot find a path within its step budget."""
    def __str__(self) -> str:
        return "Path was not found"


@dataclass
class CTNode:
    """A node in the CBS constraint tree.

    Attributes:
        constraints: The set of constraints in force at this node.
        paths: Current path per drone, keyed by drone id.
    """
    constraints: frozenset[Constraint]
    paths: dict[int, list[str]]

    @property
    def cost(self) -> float:
        """Total solution cost as the summed length of all drone paths."""
        return sum(len(p) for p in self.paths.values())

    def __lt__(self, other: "CTNode") -> bool:
        """Order nodes by cost, breaking ties by fewer constraints.

        Args:
            other: The node to compare against.

        Returns:
            True if this node should be expanded before ``other``.
        """
        if self.cost != other.cost:
            return self.cost < other.cost
        return len(self.constraints) < len(other.constraints)


type Path = list[str]
type Paths = dict[int, Path]


class CBSSolver:
    """Conflict-Based Search solver over a map graph.

    Coordinates per-drone A* searches and resolves inter-drone conflicts by
    branching the constraint tree until a conflict-free set of paths is found.
    """
    def __init__(self, graph: Graph) -> None:
        """Store the graph the solver operates on.

        Args:
            graph: The map graph providing zones, connections and drone count.
        """
        self.graph = graph

    def solve(self) -> Paths | None:
        """Run high-level CBS to find conflict-free paths for all drones.

        Builds a root node with an independent A* path per drone, then expands
        the lowest-cost constraint-tree node, detecting conflicts and branching
        by adding one constraint at a time. On success the resulting timeline
        is drawn.

        Returns:
            A mapping of drone id to its path if a conflict-free solution is
            found, otherwise ``None`` when the open list is exhausted.

        Raises:
            RuntimeError: If the search exceeds its 50-second time budget.
        """
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
        """
        root_path = {drone_id: list[path]}
        """
        root = CTNode(frozenset(), root_paths)
        open_list = [root]
        time_start = time.time()
        while open_list:
            node = heapq.heappop(open_list)  # 最小コストを展開
            if time.time() - time_start > 50:
                raise RuntimeError("CBS timeout")
            occupance_table = self._set_occupance_table(node.paths)
            conflict = self.conflict_detector(occupance_table, node.paths)
            if conflict is None:
                tl = to_timeline(node.paths)
                PlotlyVisualizer.draw(self.graph, tl)
                return node.paths  # 衝突なし → 解
            # 衝突した2機のうち一方だけ制約を追加して子ノードを1つ生成
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
                    break

        return None

    def solve2(self) -> Paths:
        """Solve greedily by prioritized planning as a CBS fallback.

        Plans drones one at a time. Before each drone, zones already filled to
        capacity by previously planned drones (excluding start/end) become
        constraints, so later drones route around them. Draws the timeline on
        success.

        Returns:
            A mapping of drone id to its path.

        Raises:
            ValueError: If no path can be found for some drone.
        """
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
        tl = to_timeline(paths)
        PlotlyVisualizer.draw(self.graph, tl)
        return paths

    def _set_occupance_table(
            self,
            paths: dict[int, list[str]]
    ) -> dict[tuple[str, int], list[int]]:
        """Index which drones occupy each (zone, time) cell.

        Connection cells (names containing ``-``) are skipped; only stationary
        zone occupancy is recorded. Used for conflict detection.
        各 (ゾーン, 時刻) に居るドローンを記録する。衝突検出に使う。
        dict[(path, time_step),list[drone_id]

        Args:
            paths: Current path per drone.

        Returns:
            A mapping from ``(zone_name, time_step)`` to the list of drone ids
            present there.
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

    def _set_con_ocpancy(
            self,
            paths: dict[int, list[str]]
    ) -> dict[tuple[str, str, int], list[int]]:
        """Index which drones traverse each connection at each time step.

        Looks at consecutive path entries, skipping connection cells and
        self-loops, and matches the move against an existing graph connection
        in either direction. 各 (origin, to, time) を通過するドローンを記録する

        Args:
            paths: Current path per drone.

        Returns:
            A mapping from ``(origin, to, time_step)`` to the list of drone ids
            traversing that connection.
        """
        conn_table: dict[tuple[str, str, int], list[int]] = {}
        for drone_id, path in paths.items():
            for t in range(1, len(path)):
                prev, curr = path[t - 1], path[t]
                if "-" in prev or "-" in curr or prev == curr:
                    continue
                key: tuple[str, str, int] | None = None
                if f"{prev}-{curr}" in self.graph.connections:
                    key = (prev, curr, t)
                elif f"{curr}-{prev}" in self.graph.connections:
                    key = (curr, prev, t)
                if key is not None:
                    conn_table.setdefault(key, []).append(drone_id)
        return conn_table

    def conflict_detector(
            self,
            occupance_table: dict[tuple[str, int], list[int]],
            paths: dict[int, list[str]],
    ) -> Conflict | None:
        """Find the first capacity violation in zones or connections.

        Checks zone occupancy against each zone's ``max_drones`` (ignoring
        time 0 and start/end zones), then connection occupancy against each
        link's ``max_link_capacity``.

        Args:
            occupance_table: Zone occupancy from :meth:`_set_occupance_table`.
            paths: Current path per drone, used to derive connection usage.

        Returns:
            The first :class:`Conflict` found, or ``None`` if all paths respect
            capacity limits.
        """
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
        for (origin, to, t), dron_ids in self._set_con_ocpancy(paths).items():
            conn = (
                self.graph.connections.get(f"{origin}-{to}")
                or self.graph.connections.get(f"{to}-{origin}")
            )
            if conn and len(dron_ids) > conn.max_link_capacity:
                return Conflict(dron_ids[0], dron_ids[1], to, t)
        return None

    def constraint_generator(self, conflict: Conflict) -> set[Constraint]:
        """Build the constraint for the second drone of a conflict.

        Args:
            conflict: The conflict to resolve.

        Returns:
            A single-element set constraining ``dron_id_b`` from the contested
            zone at the conflict's time step.
        """
        constraint_b = Constraint(
            conflict.dron_id_b, conflict.zone_name, conflict.time_step
        )
        return {constraint_b}


def to_timeline(paths: Paths) -> TimeLine:
    """Convert per-drone paths into a turn-by-turn :class:`TimeLine`.

    Drones that have already reached their goal stay at their final zone for
    the remaining turns, so all drones are represented at every time step.

    Args:
        paths: Mapping of drone id to its path.

    Returns:
        A :class:`TimeLine` with one turn per time step up to the longest path.
    """
    max_t = max(len(p) for p in paths.values())
    tl = TimeLine()
    for t in range(max_t):
        events = []
        for drone_id, path in paths.items():
            zone = path[t] if t < len(path) else path[-1]
            events.append(MoveEvent(drone_id, zone))
        tl.add_turn(events)
    return tl


def a_star(
    graph: Graph,
    start: Zone,
    goal: Zone,
    constraints: frozenset[Constraint],
    drone_id: int,
    h_scores: dict[str, int],
) -> list[str]:
    """Find a time-expanded path for one drone respecting constraints.

    Searches over ``(zone, time_step)`` states, allowing waiting in place,
    skipping blocked zones, honoring per-drone constraints, and applying small
    cost adjustments for priority zones and extra-step connections. Restricted
    zones are recorded in the reconstructed path with an explicit
    ``prev-current`` transition entry.

    Args:
        graph: The map graph being searched.
        start: The drone's start zone.
        goal: The drone's goal zone.
        constraints: Constraints in force; only those matching ``drone_id``
            apply.
        drone_id: Identifier of the drone being planned.
        h_scores: Heuristic step-distance to the goal per zone name.

    Returns:
        The path as a list of zone names (with ``prev-current`` entries for
        restricted zones), or an empty list if the goal was not reached.

    Raises:
        PathNotFoundError: If the search exceeds its time-step budget.
    """
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
            conn = graph.connections.get(f"{current.name}-{next_zone_name}")
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
        # 経路の復元 — ループを抜けた後、came_from を逆向きにたどって path を作る。
    current_state = (goal.name, time_step)
    while current_state in came_from:
        current_state_name, _ = current_state

        zone = graph.zones[current_state_name]
        if zone.zone_type == ZoneType.RESTRICTED:
            prev_state = came_from[current_state]
            extra = f"{prev_state[0]}-{current_state[0]}"
            path.append(current_state[0])
            path.append(extra)
            current_state = prev_state

        else:
            path.append(current_state[0])
            current_state = came_from[current_state]
    path.append(start.name)
    path.reverse()
    return path


def h_step_score(graph: Graph, goal: Zone) -> dict[str, int]:
    """Compute step-distance from every zone to the goal via reverse BFS.

    Builds a reverse adjacency from the graph and runs a breadth-first search
    outward from the goal, giving an admissible heuristic for A*.

    Args:
        graph: The map graph providing adjacency.
        goal: The goal zone to measure distances toward.

    Returns:
        A mapping from zone name to its step-distance to the goal. Zones
        unreachable backward from the goal are absent.
    """
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
    """Min-heap of zones keyed by f-score with stable insertion order.

    A monotonically increasing counter breaks f-score ties so that
    :class:`Zone` objects are never compared directly.
    """
    def __init__(self) -> None:
        """Initialize an empty heap and the tie-breaking counter."""
        self._heap: list[tuple[float, int, Zone, int]] = []
        self._counter = count()

    def push(self, f_score: float, zone: Zone, time_step: int) -> None:
        """Insert a zone state into the queue.

        Args:
            f_score: Priority value; lower is popped first.
            zone: The zone associated with this state.
            time_step: The time step associated with this state.
        """
        heapq.heappush(
            self._heap,
            (f_score,
             next(self._counter),
             zone,
             time_step)
        )

    def pop(self) -> tuple[Zone, int]:
        """Remove and return the lowest-f-score zone state.

        Returns:
            A ``(zone, time_step)`` tuple for the best state.
        """
        f_score, _, zone, time_step = heapq.heappop(self._heap)
        return (zone, time_step)

    def is_empty(self) -> bool:
        """Return whether the queue holds no states."""
        return len(self._heap) == 0


if __name__ == "__main__":
    file = select_file()
    graph = parser(file)
    solver = CBSSolver(graph)
    try:
        solver.solve()
    except RuntimeError:
        solver.solve2()
