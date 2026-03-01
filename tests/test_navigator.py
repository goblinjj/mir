import math
import pytest
from src.strategy.navigator import WaypointNavigator


class TestWaypointNavigator:
    def test_no_waypoints_returns_none(self):
        nav = WaypointNavigator([], arrival_radius=5)
        assert nav.get_direction((80, 90)) is None

    def test_direction_to_east(self):
        nav = WaypointNavigator([[100, 50]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 2  # East

    def test_direction_to_north(self):
        nav = WaypointNavigator([[50, 10]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 0  # North (y decreases)

    def test_direction_to_south(self):
        nav = WaypointNavigator([[50, 90]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 4  # South

    def test_direction_to_northeast(self):
        nav = WaypointNavigator([[90, 10]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 1  # NE

    def test_arrival_advances_waypoint(self):
        nav = WaypointNavigator([[50, 50], [100, 100]], arrival_radius=5)
        assert nav.current_index == 0
        # Move close to first waypoint
        nav.get_direction((50, 52))  # within radius
        assert nav.current_index == 1  # advanced to next

    def test_loop_back_to_start(self):
        nav = WaypointNavigator([[50, 50], [100, 100]], arrival_radius=5)
        nav.current_index = 1
        nav.get_direction((100, 102))  # arrive at last waypoint
        assert nav.current_index == 0  # loop back

    def test_teleport_finds_nearest(self):
        nav = WaypointNavigator([[10, 10], [90, 90], [50, 50]], arrival_radius=5)
        nav.current_index = 0
        nav.handle_teleport((88, 92))
        assert nav.current_index == 1  # closest to (90, 90)

    def test_set_waypoints(self):
        nav = WaypointNavigator([], arrival_radius=5)
        nav.set_waypoints([[10, 20], [30, 40]])
        assert len(nav.waypoints) == 2
        assert nav.current_index == 0
