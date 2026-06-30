import pytest
from time_line import DroneState, MoveEvent, TimeLine
from find_path import to_timeline


def test_get_state_zone() -> None:
    tl = TimeLine()
    tl.add_turn([
        MoveEvent(drone=0, to="zoneA"), MoveEvent(drone=1, to="zoneB")
    ])
    assert tl.get_state(0, 0) == DroneState(
        id=0, location="zoneA", status="zone"
    )


def test_get_state_connection() -> None:
    tl = TimeLine()
    tl.add_turn([MoveEvent(drone=0, to="zoneA-restricted_B")])
    state = tl.get_state(0, 0)
    assert state.status == "connection"
    assert state.location == "zoneA-restricted_B"


def test_get_state_not_found() -> None:
    tl = TimeLine()
    tl.add_turn([MoveEvent(drone=0, to="zoneA")])
    with pytest.raises(KeyError):
        tl.get_state(0, 99)


def test_to_timeline_turn_count() -> None:
    paths = {0: ["A", "B", "C"], 1: ["A", "B", "C"]}
    tl = to_timeline(paths)
    assert len(tl.turns) == 3


def test_to_timeline_locations() -> None:
    paths = {0: ["A", "B"], 1: ["A", "C"]}
    tl = to_timeline(paths)
    assert tl.get_state(0, 0).location == "A"
    assert tl.get_state(1, 1).location == "C"


def test_to_timeline_short_path_extended() -> None:
    paths = {0: ["A", "B", "C"], 1: ["A", "B"]}
    tl = to_timeline(paths)
    assert len(tl.turns) == 3
    assert tl.get_state(2, 1).location == "B"


def test_to_timeline_connection_status() -> None:
    paths = {0: ["A", "A-restricted_B", "B"]}
    tl = to_timeline(paths)
    assert tl.get_state(1, 0).status == "connection"
