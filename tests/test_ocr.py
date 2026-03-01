"""Tests for OCR monster detection."""

import numpy as np
import pytest

from src.vision.ocr import MonsterDetector, DetectedMonster, _SCALE_FACTOR, _HAS_CV2


def test_detected_monster_dataclass():
    m = DetectedMonster(name="鸡", x=400, y=300, confidence=0.95)
    assert m.name == "鸡"
    assert m.x == 400
    assert m.y == 300
    assert m.confidence == 0.95


def test_monster_detector_init():
    md = MonsterDetector()
    assert md.ocr_engine is not None


def test_classify_monster_type():
    md = MonsterDetector()
    assert md.classify("鸡") == "normal"
    assert md.classify("祖玛教主") == "boss"
    md2 = MonsterDetector(boss_names=["测试Boss"])
    assert md2.classify("测试Boss") == "boss"
    assert md2.classify("小鸡") == "normal"


@pytest.mark.skipif(not _HAS_CV2, reason="cv2 not available")
class TestPreprocessFrame:
    """Tests for MonsterDetector.preprocess_frame()."""

    def test_output_shape_is_scaled(self):
        """Output should be 2x the input dimensions."""
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        result = MonsterDetector.preprocess_frame(frame)
        assert result.shape == (100 * _SCALE_FACTOR, 200 * _SCALE_FACTOR)

    def test_white_pixels_preserved(self):
        """White pixels (text) should survive as dark pixels in inverted output."""
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        # Draw a white block (simulating text)
        frame[20:30, 20:30] = 255
        result = MonsterDetector.preprocess_frame(frame)
        # In the inverted output, white text becomes dark (0) on white (255) background
        # Check the scaled region has dark pixels
        region = result[20 * _SCALE_FACTOR:30 * _SCALE_FACTOR,
                        20 * _SCALE_FACTOR:30 * _SCALE_FACTOR]
        assert np.mean(region) < 128  # mostly dark (text area)

    def test_dark_pixels_filtered(self):
        """Non-white pixels should be filtered out (become white background)."""
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        frame[20:30, 20:30] = 100  # gray, not white
        result = MonsterDetector.preprocess_frame(frame)
        # Everything should be white (255) in the output since no white text
        assert np.mean(result) > 250

    def test_grayscale_input(self):
        """Should handle single-channel input."""
        frame = np.zeros((50, 50), dtype=np.uint8)
        frame[20:30, 20:30] = 255
        result = MonsterDetector.preprocess_frame(frame)
        assert result.shape == (50 * _SCALE_FACTOR, 50 * _SCALE_FACTOR)

    def test_empty_frame(self):
        """All-black frame should produce all-white output."""
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        result = MonsterDetector.preprocess_frame(frame)
        assert np.all(result == 255)
