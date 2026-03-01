"""Waypoint-based navigation using minimap coordinates."""

import math
from typing import List, Optional, Tuple


class WaypointNavigator:
    """Navigates between waypoints on the minimap."""

    # 8 directions: N, NE, E, SE, S, SW, W, NW
    # Angle ranges centered on each direction (in degrees, 0=East, CCW positive)
    _DIR_ANGLES = [90, 45, 0, 315, 270, 225, 180, 135]  # East=0°, North=90°

    def __init__(self, waypoints: List[List[int]], arrival_radius: int = 5):
        self.waypoints = waypoints
        self.arrival_radius = arrival_radius
        self.current_index = 0

    def get_direction(self, current_pos: Tuple[int, int]) -> Optional[int]:
        """Get the 8-direction index to move toward the current waypoint.

        Args:
            current_pos: (x, y) current player position on minimap.

        Returns:
            Direction index 0-7 (N, NE, E, SE, S, SW, W, NW) or None.
        """
        if not self.waypoints:
            return None

        tx, ty = self.waypoints[self.current_index]
        cx, cy = current_pos

        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy)

        # Check arrival
        if dist <= self.arrival_radius:
            self.current_index = (self.current_index + 1) % len(self.waypoints)
            # Recalculate for new target
            tx, ty = self.waypoints[self.current_index]
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)
            if dist <= self.arrival_radius:
                return None  # Already at next waypoint too

        # Convert to angle (screen coords: y increases downward)
        # atan2 with negated dy so that up = positive angle
        angle_rad = math.atan2(-dy, dx)
        angle_deg = math.degrees(angle_rad) % 360

        # Map angle to nearest 8-direction
        # N=90°, NE=45°, E=0°, SE=315°, S=270°, SW=225°, W=180°, NW=135°
        best_dir = 0
        best_diff = 360
        for i, dir_angle in enumerate(self._DIR_ANGLES):
            diff = abs(angle_deg - dir_angle)
            if diff > 180:
                diff = 360 - diff
            if diff < best_diff:
                best_diff = diff
                best_dir = i
        return best_dir

    def handle_teleport(self, current_pos: Tuple[int, int]) -> None:
        """After teleport, find the nearest waypoint and set it as target."""
        if not self.waypoints:
            return
        cx, cy = current_pos
        best_idx = 0
        best_dist = float("inf")
        for i, (wx, wy) in enumerate(self.waypoints):
            d = math.hypot(wx - cx, wy - cy)
            if d < best_dist:
                best_dist = d
                best_idx = i
        self.current_index = best_idx

    def set_waypoints(self, waypoints: List[List[int]]) -> None:
        """Replace waypoints and reset index."""
        self.waypoints = waypoints
        self.current_index = 0

    @property
    def current_target(self) -> Optional[List[int]]:
        """Return the current target waypoint or None."""
        if not self.waypoints:
            return None
        return self.waypoints[self.current_index]
