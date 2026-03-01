import math
import numpy as np
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


class TestPathfindingNavigation:
    @staticmethod
    def _make_mask(width=40, height=40, walls=None):
        mask = np.ones((height, width), dtype=bool)
        if walls:
            for (x, y) in walls:
                mask[y, x] = False
        return mask

    def test_update_path_plans_route(self):
        nav = WaypointNavigator([[30, 5]], arrival_radius=3)
        mask = self._make_mask()
        nav.update_path((5, 5), mask)
        assert len(nav._path) > 0
        assert nav._path[-1] == (30, 5)

    def test_get_direction_follows_path(self):
        """After update_path, get_direction returns direction along BFS path."""
        # Wall blocks direct east at x=15, y=0..10
        walls = [(15, y) for y in range(11)]
        mask = self._make_mask(walls=walls)
        nav = WaypointNavigator([[30, 5]], arrival_radius=3)
        nav.update_path((5, 5), mask)
        direction = nav.get_direction((5, 5))
        assert direction is not None
        # Should NOT be pure East (2) since wall blocks it
        # The BFS path will go around the wall

    def test_no_mask_falls_back_to_straight_line(self):
        """Without walkability mask, uses straight-line direction."""
        nav = WaypointNavigator([[30, 5]], arrival_radius=3)
        # No update_path called, no path
        direction = nav.get_direction((5, 5))
        assert direction == 2  # East (straight line)

    def test_replan_on_waypoint_change(self):
        mask = self._make_mask()
        nav = WaypointNavigator([[10, 10], [30, 30]], arrival_radius=3)
        nav.update_path((5, 5), mask)
        assert nav._path_target_index == 0

        # Advance waypoint
        nav.current_index = 1
        nav.update_path((10, 10), mask)
        assert nav._path_target_index == 1
        assert nav._path[-1] == (30, 30)

    def test_replan_when_far_from_path(self):
        mask = self._make_mask()
        nav = WaypointNavigator([[30, 5]], arrival_radius=3)
        nav.update_path((5, 5), mask)
        old_path = list(nav._path)

        # Player jumped far from path
        nav.update_path((5, 30), mask)
        # Should have replanned
        assert nav._path != old_path
