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

    def test_detect_brightest_cluster(self):
        """If multiple bright areas, return the one with most white pixels."""
        frame = _make_frame(dots=[(30, 30), (80, 90)])
        # Add extra white pixels around (80, 90) to make it the larger cluster
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                ny, nx = 90 + dy, 80 + dx
                if 0 <= ny < 180 and 0 <= nx < 160:
                    frame[ny, nx] = (255, 255, 255)
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        assert abs(x - 80) <= 2
        assert abs(y - 90) <= 2
