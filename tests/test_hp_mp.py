"""Tests for HP/MP bar recognition."""

import numpy as np
import pytest

from src.vision.hp_mp import HpMpDetector


@pytest.fixture
def detector():
    return HpMpDetector(
        hp_color_min=np.array([0, 0, 180]),
        hp_color_max=np.array([80, 80, 255]),
        mp_color_min=np.array([180, 0, 0]),
        mp_color_max=np.array([255, 80, 80]),
    )


def test_full_hp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [10, 10, 200]  # BGR: full red
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert ratio > 0.9


def test_half_hp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :80] = [10, 10, 200]  # Left half red
    bar[:, 80:] = [30, 30, 30]   # Right half dark
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert 0.4 < ratio < 0.6


def test_empty_hp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [30, 30, 30]  # All dark
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert ratio < 0.1


def test_full_mp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [200, 10, 10]  # BGR: full blue
    ratio = detector.detect_bar_ratio(bar, "mp")
    assert ratio > 0.9
