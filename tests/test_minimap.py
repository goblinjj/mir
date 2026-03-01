import numpy as np
import pytest
from src.vision.minimap import MinimapAnalyzer


def _make_frame(width=160, height=180, dots=None, bg_color=(40, 40, 40)):
    """Create a fake minimap frame with optional white dots."""
    frame = np.full((height, width, 3), bg_color, dtype=np.uint8)
    if dots:
        for (x, y) in dots:
            # Draw a 3x3 white dot
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        frame[ny, nx] = (255, 255, 255)
    return frame


class TestWhiteDotDetection:
    def setup_method(self):
        self.analyzer = MinimapAnalyzer(white_threshold=240, black_threshold=15)

    def test_detect_single_white_dot(self):
        frame = _make_frame(dots=[(80, 90)])
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        assert abs(x - 80) <= 1
        assert abs(y - 90) <= 1

    def test_detect_no_dot_returns_none(self):
        frame = _make_frame()  # no dots
        pos = self.analyzer.detect_player_position(frame)
        assert pos is None

    def test_detect_dot_ignores_dim_pixels(self):
        """Pixels below threshold should not be detected."""
        frame = _make_frame(bg_color=(200, 200, 200))  # bright but below 240
        pos = self.analyzer.detect_player_position(frame)
        assert pos is None

    def test_detect_small_dot_ignores_large_portal(self):
        """Player dot (small) should be detected, portal icon (large) ignored."""
        frame = _make_frame(dots=[(30, 30)])  # small player dot (3x3 = 9px)
        # Add a large portal-like white shape at (80, 90)
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                ny, nx = 90 + dy, 80 + dx
                if 0 <= ny < 180 and 0 <= nx < 160:
                    frame[ny, nx] = (255, 255, 255)
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        # Should pick the small dot at (30, 30), not the large portal
        assert abs(x - 30) <= 1
        assert abs(y - 30) <= 1

    def test_detect_ignores_elongated_portal_strokes(self):
        """Thin elongated white strokes (portal parts) are filtered out."""
        frame = _make_frame(dots=[(80, 90)])  # 3x3 compact player dot
        # Add a thin vertical stroke (portal piece): 2x10 = 20 pixels
        for dy in range(10):
            frame[30 + dy, 50] = (255, 255, 255)
            frame[30 + dy, 51] = (255, 255, 255)
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        # Should pick the compact dot at (80, 90), not the elongated stroke
        assert abs(x - 80) <= 1
        assert abs(y - 90) <= 1

    def test_detect_ignores_noise_pixels(self):
        """Single stray white pixels are filtered out."""
        frame = _make_frame(dots=[(80, 90)])  # 3x3 = 9px dot
        frame[50, 50] = (255, 255, 255)  # 1px noise
        frame[20, 20] = (255, 255, 255)  # 1px noise
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        assert abs(x - 80) <= 1
        assert abs(y - 90) <= 1


class TestWalkability:
    def setup_method(self):
        self.analyzer = MinimapAnalyzer(white_threshold=240, black_threshold=15)

    def test_black_is_not_walkable(self):
        frame = _make_frame(bg_color=(0, 0, 0))  # all black
        assert not self.analyzer.is_walkable(frame, 80, 90)

    def test_non_black_is_walkable(self):
        frame = _make_frame(bg_color=(60, 50, 40))  # brownish = walkable
        assert self.analyzer.is_walkable(frame, 80, 90)

    def test_walkability_mask_shape(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        mask = self.analyzer.get_walkability_mask(frame)
        assert mask.shape == (180, 160)
        assert mask.dtype == bool

    def test_walkability_mask_mixed(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        # Paint a black rectangle (wall)
        frame[50:80, 30:60] = (0, 0, 0)
        mask = self.analyzer.get_walkability_mask(frame)
        assert not mask[65, 45]  # inside black area
        assert mask[10, 10]      # outside black area

    def test_is_walkable_out_of_bounds(self):
        frame = _make_frame()
        assert not self.analyzer.is_walkable(frame, -1, 0)
        assert not self.analyzer.is_walkable(frame, 0, 999)


class TestErosion:
    def setup_method(self):
        self.analyzer = MinimapAnalyzer(white_threshold=240, black_threshold=15)

    def test_erode_shrinks_walkable_area(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        frame[50:80, 30:60] = (0, 0, 0)  # wall block
        raw = self.analyzer.get_walkability_mask(frame, erode=0)
        eroded = self.analyzer.get_walkability_mask(frame, erode=2)
        # Eroded should have fewer walkable pixels
        assert np.sum(eroded) < np.sum(raw)
        # Pixels at wall edge should be eroded away
        assert raw[49, 35]       # just above wall, walkable in raw
        assert not eroded[49, 35]  # but not after erosion (within 2px of wall)

    def test_erode_zero_is_noop(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        raw = self.analyzer.get_walkability_mask(frame, erode=0)
        also_raw = self.analyzer.get_walkability_mask(frame)
        assert np.array_equal(raw, also_raw)


class TestFindPath:
    """BFS pathfinding on walkability mask."""

    @staticmethod
    def _make_mask(width=20, height=20, walls=None):
        """Create a small walkability mask with optional wall cells."""
        mask = np.ones((height, width), dtype=bool)
        if walls:
            for (x, y) in walls:
                mask[y, x] = False
        return mask

    def test_straight_line_path(self):
        mask = self._make_mask()
        path = MinimapAnalyzer.find_path(mask, (0, 0), (5, 0))
        assert len(path) > 0
        assert path[0] == (0, 0)
        assert path[-1] == (5, 0)

    def test_path_around_wall(self):
        # Wall blocks direct east path at x=3, y=0..2
        walls = [(3, y) for y in range(3)]
        mask = self._make_mask(walls=walls)
        path = MinimapAnalyzer.find_path(mask, (0, 0), (5, 0))
        assert len(path) > 0
        assert path[-1] == (5, 0)
        # Path must not cross the wall
        for (x, y) in path:
            assert mask[y, x], f"Path crosses wall at ({x},{y})"

    def test_unreachable_returns_empty(self):
        # Surround goal with walls
        walls = [(4, 4), (5, 4), (6, 4), (4, 5), (6, 5), (4, 6), (5, 6), (6, 6)]
        mask = self._make_mask(walls=walls)
        path = MinimapAnalyzer.find_path(mask, (0, 0), (5, 5))
        assert path == []

    def test_start_on_wall_returns_empty(self):
        mask = self._make_mask(walls=[(0, 0)])
        path = MinimapAnalyzer.find_path(mask, (0, 0), (5, 5))
        assert path == []

    def test_goal_on_wall_returns_empty(self):
        mask = self._make_mask(walls=[(5, 5)])
        path = MinimapAnalyzer.find_path(mask, (0, 0), (5, 5))
        assert path == []

    def test_same_start_goal(self):
        mask = self._make_mask()
        path = MinimapAnalyzer.find_path(mask, (3, 3), (3, 3))
        assert path == [(3, 3)]
