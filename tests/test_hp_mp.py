"""Tests for HP/MP text-based detection."""

import numpy as np
import pytest

from src.vision.hp_mp import HpMpDetector, _parse_ratio


class TestParseRatio:
    def test_normal(self):
        assert abs(_parse_ratio("211/211") - 1.0) < 0.01

    def test_partial(self):
        assert abs(_parse_ratio("100/200") - 0.5) < 0.01

    def test_with_spaces(self):
        assert abs(_parse_ratio("814 / 816") - 0.998) < 0.01

    def test_zero_current(self):
        assert abs(_parse_ratio("0/500") - 0.0) < 0.01

    def test_no_match(self):
        assert _parse_ratio("no numbers here") == -1.0

    def test_empty(self):
        assert _parse_ratio("") == -1.0

    def test_zero_max(self):
        assert _parse_ratio("100/0") == -1.0

    def test_noisy_text(self):
        # OCR might return extra chars
        assert abs(_parse_ratio("HP: 150/300 ok") - 0.5) < 0.01


class TestHpMpDetector:
    def test_init_without_ocr(self):
        """Detector initializes gracefully without OCR engine."""
        det = HpMpDetector()
        assert det._last_hp_ratio == 1.0
        assert det._last_mp_ratio == 1.0

    def test_detect_returns_last_known_on_failure(self):
        """When OCR is unavailable, returns last known good values."""
        det = HpMpDetector()
        det._last_hp_ratio = 0.8
        det._last_mp_ratio = 0.6
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        hp, mp = det.detect_hp_mp(frame, [0, 0, 50, 20], [50, 0, 50, 20])
        assert hp == 0.8
        assert mp == 0.6

    def test_detect_ratio_from_text_no_ocr(self):
        """Returns -1.0 when no OCR engine available."""
        det = HpMpDetector()
        det.ocr = None
        img = np.zeros((20, 60, 3), dtype=np.uint8)
        assert det.detect_ratio_from_text(img) == -1.0

    def test_detect_ratio_from_text_empty_image(self):
        det = HpMpDetector()
        assert det.detect_ratio_from_text(None) == -1.0
        assert det.detect_ratio_from_text(np.array([])) == -1.0

    def test_legacy_detect_bar_ratio(self):
        """Legacy interface returns 0.0 when OCR unavailable."""
        det = HpMpDetector()
        det.ocr = None
        img = np.zeros((20, 60, 3), dtype=np.uint8)
        assert det.detect_bar_ratio(img, "hp") == 0.0
