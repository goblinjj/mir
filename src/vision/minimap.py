"""Minimap analysis: player position detection and walkability mask."""

from typing import Optional, Tuple

import numpy as np


class MinimapAnalyzer:
    """Analyzes minimap screenshots for player position and terrain."""

    def __init__(self, white_threshold: int = 240, black_threshold: int = 15):
        self.white_threshold = white_threshold
        self.black_threshold = black_threshold

    def detect_player_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """Detect the white dot (player) on the minimap frame.

        Args:
            frame: BGR or RGB minimap image (H, W, 3).

        Returns:
            (x, y) pixel coordinates of the player dot, or None if not found.
        """
        if frame is None or frame.size == 0:
            return None

        # All channels must be above threshold (white dot)
        min_channel = np.min(frame, axis=2)
        white_mask = min_channel >= self.white_threshold

        if not np.any(white_mask):
            return None

        # Label connected components to find the largest white cluster
        labeled = self._label_components(white_mask)
        if labeled is None:
            return None

        # Find the label with the most pixels
        labels = labeled[labeled > 0]
        if len(labels) == 0:
            return None

        unique, counts = np.unique(labels, return_counts=True)
        best_label = unique[np.argmax(counts)]

        ys, xs = np.where(labeled == best_label)
        cx = int(np.mean(xs))
        cy = int(np.mean(ys))
        return (cx, cy)

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

    def get_walkability_mask(self, frame: np.ndarray) -> np.ndarray:
        """Generate walkability mask from minimap frame.

        Returns:
            Boolean array (H, W) where True = walkable, False = wall/boundary.
        """
        max_channel = np.max(frame, axis=2)
        return max_channel >= self.black_threshold

    def is_walkable(self, frame: np.ndarray, x: int, y: int) -> bool:
        """Check if a specific minimap pixel is walkable."""
        h, w = frame.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return False
        return int(np.max(frame[y, x])) >= self.black_threshold
