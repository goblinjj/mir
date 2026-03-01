"""Minimap analysis: player position detection and walkability mask."""

from collections import deque
from typing import List, Optional, Tuple

import numpy as np


class MinimapAnalyzer:
    """Analyzes minimap screenshots for player position and terrain."""

    def __init__(self, white_threshold: int = 240, black_threshold: int = 15):
        self.white_threshold = white_threshold
        self.black_threshold = black_threshold

    # Player dot: small (3x3 to 5x5 = 9-25 pixels), compact (square-ish).
    # Portal icons: larger or elongated strokes.
    _DOT_MIN_PIXELS = 4
    _DOT_MAX_PIXELS = 30
    _DOT_MIN_COMPACTNESS = 0.5  # fill ratio of bounding box

    def detect_player_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """Detect the white dot (player) on the minimap frame.

        The player dot is a small, compact white cluster (~9-25 pixels).
        Larger or elongated white shapes (portal icons, text) are filtered out.

        Args:
            frame: BGR or RGB minimap image (H, W, 3).

        Returns:
            (x, y) pixel coordinates of the player dot, or None if not found.
        """
        if frame is None or frame.size == 0:
            return None

        min_channel = np.min(frame, axis=2)
        white_mask = min_channel >= self.white_threshold

        if not np.any(white_mask):
            return None

        labeled = self._label_components(white_mask)
        if labeled is None:
            return None

        unique, counts = np.unique(labeled[labeled > 0], return_counts=True)
        if len(unique) == 0:
            return None

        # Score each candidate cluster by how "dot-like" it is
        best_pos = None
        best_score = -1

        for i in range(len(unique)):
            pixel_count = counts[i]
            if pixel_count < self._DOT_MIN_PIXELS:
                continue
            if pixel_count > self._DOT_MAX_PIXELS:
                continue

            label = unique[i]
            ys, xs = np.where(labeled == label)
            bbox_w = int(xs.max() - xs.min()) + 1
            bbox_h = int(ys.max() - ys.min()) + 1
            compactness = pixel_count / (bbox_w * bbox_h)

            if compactness < self._DOT_MIN_COMPACTNESS:
                continue  # elongated shape (portal stroke), skip

            # Score: prefer compact clusters of typical dot size (9-16 px)
            size_score = 1.0 - abs(pixel_count - 12) / 20.0
            score = compactness + max(0, size_score)

            if score > best_score:
                best_score = score
                best_pos = (int(np.mean(xs)), int(np.mean(ys)))

        return best_pos

    @staticmethod
    def _label_components(mask: np.ndarray) -> np.ndarray:
        """Simple connected-component labeling (4-connectivity)."""
        labeled = np.zeros_like(mask, dtype=np.int32)
        current_label = 0
        h, w = mask.shape

        for y in range(h):
            for x in range(w):
                if mask[y, x] and labeled[y, x] == 0:
                    current_label += 1
                    # BFS flood fill
                    stack = [(y, x)]
                    while stack:
                        cy, cx = stack.pop()
                        if labeled[cy, cx] != 0:
                            continue
                        labeled[cy, cx] = current_label
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labeled[ny, nx] == 0:
                                stack.append((ny, nx))

        return labeled if current_label > 0 else None

    def get_walkability_mask(self, frame: np.ndarray,
                             erode: int = 0) -> np.ndarray:
        """Generate walkability mask from minimap frame.

        Args:
            frame: BGR or RGB minimap image (H, W, 3).
            erode: Number of erosion iterations (shrinks walkable area by
                   this many pixels, creating a safety margin around walls).

        Returns:
            Boolean array (H, W) where True = walkable, False = wall/boundary.
        """
        max_channel = np.max(frame, axis=2)
        mask = max_channel >= self.black_threshold
        if erode > 0:
            mask = self._erode_mask(mask, erode)
        return mask

    @staticmethod
    def _erode_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
        """Erode walkability mask (4-neighbor) to create wall safety margin."""
        result = mask.copy()
        for _ in range(iterations):
            eroded = result.copy()
            eroded[1:, :] &= result[:-1, :]
            eroded[:-1, :] &= result[1:, :]
            eroded[:, 1:] &= result[:, :-1]
            eroded[:, :-1] &= result[:, 1:]
            result = eroded
        return result

    @staticmethod
    def find_path(
        mask: np.ndarray,
        start: Tuple[int, int],
        goal: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """BFS pathfinding on the walkability mask (8-direction).

        Args:
            mask: Boolean array (H, W), True = walkable.
            start: (x, y) start position.
            goal: (x, y) goal position.

        Returns:
            List of (x, y) waypoints from start to goal (inclusive),
            or empty list if unreachable.
        """
        sx, sy = start
        gx, gy = goal
        h, w = mask.shape

        # Bounds / walkability check
        if not (0 <= sy < h and 0 <= sx < w and mask[sy, sx]):
            return []
        if not (0 <= gy < h and 0 <= gx < w and mask[gy, gx]):
            return []
        if (sx, sy) == (gx, gy):
            return [(sx, sy)]

        # 8-direction offsets: N, NE, E, SE, S, SW, W, NW
        _DIRS = [(0, -1), (1, -1), (1, 0), (1, 1),
                 (0, 1), (-1, 1), (-1, 0), (-1, -1)]

        visited = np.zeros((h, w), dtype=bool)
        visited[sy, sx] = True
        # Store parent as flat index; -1 = start
        parent = np.full(h * w, -1, dtype=np.int32)
        queue = deque()
        queue.append((sx, sy))

        found = False
        while queue:
            cx, cy = queue.popleft()
            for ddx, ddy in _DIRS:
                nx, ny = cx + ddx, cy + ddy
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and mask[ny, nx]:
                    visited[ny, nx] = True
                    parent[ny * w + nx] = cy * w + cx
                    if nx == gx and ny == gy:
                        found = True
                        break
                    queue.append((nx, ny))
            if found:
                break

        if not found:
            return []

        # Reconstruct path
        path = []
        idx = gy * w + gx
        while idx != -1:
            y_p, x_p = divmod(idx, w)
            path.append((x_p, y_p))
            idx = parent[idx]
        path.reverse()
        return path

    def is_walkable(self, frame: np.ndarray, x: int, y: int) -> bool:
        """Check if a specific minimap pixel is walkable."""
        h, w = frame.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return False
        return int(np.max(frame[y, x])) >= self.black_threshold
