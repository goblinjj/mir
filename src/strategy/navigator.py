"""Waypoint-based navigation using minimap coordinates."""

import math
from typing import List, Optional, Tuple

import numpy as np

from src.vision.minimap import MinimapAnalyzer
from src.utils.logger import log


class WaypointNavigator:
    """Navigates between waypoints on the minimap using BFS pathfinding."""

    # 8 directions: N, NE, E, SE, S, SW, W, NW
    # Angle ranges centered on each direction (in degrees, 0=East, CCW positive)
    _DIR_ANGLES = [90, 45, 0, 315, 270, 225, 180, 135]  # East=0°, North=90°

    # 8-direction deltas matching direction indices: N, NE, E, SE, S, SW, W, NW
    _DIR_DELTAS = [(0, -1), (1, -1), (1, 0), (1, 1),
                   (0, 1), (-1, 1), (-1, 0), (-1, -1)]

    def __init__(self, waypoints: List[List[int]], arrival_radius: int = 5):
        self.waypoints = waypoints
        self.arrival_radius = arrival_radius
        self.current_index = 0
        # BFS path state
        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._path_target_index: int = -1  # which waypoint was this path for
        # How far ahead on the path to look for next step (skip nearby points)
        self._path_step_size = 8

    def update_path(self, current_pos: Tuple[int, int],
                    walkability_mask: Optional[np.ndarray] = None,
                    raw_mask: Optional[np.ndarray] = None,
                    force: bool = False) -> None:
        """Compute or update the BFS path to current waypoint.

        Tries the (eroded) walkability_mask first for center-of-corridor paths.
        Falls back to raw_mask if the eroded mask blocks the route.

        Args:
            current_pos: (x, y) player position on minimap.
            walkability_mask: Eroded boolean mask (H, W) — preferred for paths.
            raw_mask: Original boolean mask (H, W) — fallback for tight spaces.
            force: Force recomputation even if path looks valid.
        """
        if not self.waypoints or walkability_mask is None:
            self._path = []
            return

        target = self.waypoints[self.current_index]
        needs_replan = force or self._needs_replan(current_pos, target)

        if not needs_replan:
            return

        goal = (target[0], target[1])

        # If player is on eroded-away area, find nearest walkable start
        start = current_pos
        h, w = walkability_mask.shape
        sx, sy = start
        if 0 <= sy < h and 0 <= sx < w and not walkability_mask[sy, sx]:
            start = self._nearest_walkable(walkability_mask, current_pos)
            if start:
                log.info("Navigator: player near wall, shifted start %s -> %s",
                         current_pos, start)

        # Also check goal
        eroded_goal = goal
        gx, gy = goal
        if 0 <= gy < h and 0 <= gx < w and not walkability_mask[gy, gx]:
            eroded_goal = self._nearest_walkable(walkability_mask, goal)

        path = []
        if start and eroded_goal:
            path = MinimapAnalyzer.find_path(walkability_mask, start, eroded_goal)

        # Fallback: if eroded mask blocks path, try raw mask
        if not path and raw_mask is not None:
            path = MinimapAnalyzer.find_path(raw_mask, current_pos, goal)
            if path:
                log.info("Navigator: using raw mask fallback (eroded too tight)")

        self._path = path
        self._path_index = 0
        self._path_target_index = self.current_index

        if path:
            preview = path[:10]
            log.info("Navigator: planned path with %d steps to waypoint %d, "
                     "start=%s, first steps: %s",
                     len(path), self.current_index, current_pos, preview)
        else:
            log.warning("Navigator: no path found to waypoint %d (%s)",
                        self.current_index, target)

    def _needs_replan(self, current_pos: Tuple[int, int],
                      target: List[int]) -> bool:
        """Check if we need to recompute the path."""
        # No path yet
        if not self._path:
            return True
        # Target waypoint changed
        if self._path_target_index != self.current_index:
            return True
        # Player drifted too far from the path — find closest point
        min_dist = float("inf")
        best_idx = self._path_index
        search_end = min(self._path_index + 20, len(self._path))
        for i in range(self._path_index, search_end):
            px, py = self._path[i]
            d = abs(px - current_pos[0]) + abs(py - current_pos[1])
            if d < min_dist:
                min_dist = d
                best_idx = i
        if min_dist <= 5:
            # Snap to closest path point
            self._path_index = best_idx
            return False
        return True

    def get_direction(self, current_pos: Tuple[int, int]) -> Optional[int]:
        """Get the 8-direction index to move toward the current waypoint.

        Uses the BFS path if available, otherwise falls back to straight-line.

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
            self._path = []  # clear path for next waypoint
            # Recalculate for new target
            tx, ty = self.waypoints[self.current_index]
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)
            if dist <= self.arrival_radius:
                return None  # Already at next waypoint too

        # Try BFS path first
        if self._path and self._path_index < len(self._path):
            direction = self._direction_from_path(current_pos)
            if direction is not None:
                return direction

        # Fallback: straight-line direction
        fallback = self._straight_line_direction(dx, dy)
        log.info("Navigator: FALLBACK straight-line to waypoint, "
                 "path_len=%d path_idx=%d dir=%s",
                 len(self._path), self._path_index,
                 self._DIR_NAMES[fallback])
        return fallback

    _DIR_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def _direction_from_path(self, current_pos: Tuple[int, int]) -> Optional[int]:
        """Get direction from current position toward the next path point."""
        # Look a few steps ahead on the path to avoid micro-jitter
        look_idx = min(self._path_index + self._path_step_size,
                       len(self._path) - 1)
        px, py = self._path[look_idx]
        cx, cy = current_pos

        ddx = px - cx
        ddy = py - cy
        if ddx == 0 and ddy == 0:
            # Advance path index
            self._path_index = look_idx
            return None

        # Map delta to nearest 8-direction
        angle_rad = math.atan2(-ddy, ddx)
        angle_deg = math.degrees(angle_rad) % 360
        direction = self._angle_to_direction(angle_deg)
        log.info("PathDir: pos=%s path[%d]=%s dx=%d dy=%d angle=%.0f dir=%s",
                 current_pos, look_idx, (px, py), ddx, ddy, angle_deg,
                 self._DIR_NAMES[direction])
        return direction

    def _straight_line_direction(self, dx: int, dy: int) -> int:
        """Compute 8-direction from dx/dy delta (straight-line fallback)."""
        angle_rad = math.atan2(-dy, dx)
        angle_deg = math.degrees(angle_rad) % 360
        return self._angle_to_direction(angle_deg)

    def _angle_to_direction(self, angle_deg: float) -> int:
        """Map an angle in degrees to nearest 8-direction index."""
        best_dir = 0
        best_diff = 360.0
        for i, dir_angle in enumerate(self._DIR_ANGLES):
            diff = abs(angle_deg - dir_angle)
            if diff > 180:
                diff = 360 - diff
            if diff < best_diff:
                best_diff = diff
                best_dir = i
        return best_dir

    @staticmethod
    def _nearest_walkable(mask: np.ndarray, pos: Tuple[int, int],
                          max_radius: int = 10) -> Optional[Tuple[int, int]]:
        """Find the nearest walkable pixel to pos on the mask."""
        x, y = pos
        h, w = mask.shape
        for r in range(1, max_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) != r and abs(dy) != r:
                        continue  # only check perimeter
                    nx, ny = x + dx, y + dy
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                        return (nx, ny)
        return None

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
        self._path = []  # force replan

    def set_waypoints(self, waypoints: List[List[int]]) -> None:
        """Replace waypoints and reset index."""
        self.waypoints = waypoints
        self.current_index = 0
        self._path = []

    @property
    def current_target(self) -> Optional[List[int]]:
        """Return the current target waypoint or None."""
        if not self.waypoints:
            return None
        return self.waypoints[self.current_index]
