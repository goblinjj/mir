"""Tests for OCR monster detection."""

import pytest

from src.vision.ocr import MonsterDetector, DetectedMonster


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
