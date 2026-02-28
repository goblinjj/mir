"""Tests for window manager (platform-independent logic only)."""

import pytest

from src.capture.window import GameWindow


def test_game_window_init():
    gw = GameWindow(window_title="测试窗口")
    assert gw.window_title == "测试窗口"
    assert gw.hwnd is None


def test_game_window_not_found():
    gw = GameWindow(window_title="不存在的窗口_XYZ_12345")
    found = gw.find_window()
    assert found is False
    assert gw.hwnd is None
