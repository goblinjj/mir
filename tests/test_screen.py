"""Tests for screen capture (platform-independent logic)."""

import numpy as np
import pytest

from src.capture.screen import ScreenCapture


def test_screen_capture_init():
    sc = ScreenCapture()
    assert sc.last_frame is None


def test_crop_region():
    sc = ScreenCapture()
    # Simulate a 600x800 RGB image
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    frame[40:52, 10:170] = [255, 0, 0]  # Red bar region

    cropped = sc.crop_region(frame, [10, 40, 160, 12])
    assert cropped.shape == (12, 160, 3)
    assert np.all(cropped[0, 0] == [255, 0, 0])
