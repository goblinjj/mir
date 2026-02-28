"""Tests for action executor."""

import pytest

from src.action.executor import ActionExecutor


class FakeKeyboard:
    def __init__(self):
        self.pressed = []
    def press_key(self, key, hold_time=0.05):
        self.pressed.append(key)


class FakeMouse:
    def __init__(self):
        self.clicks = []
    def click(self, x, y, button="left"):
        self.clicks.append((x, y, button))


def test_executor_use_skill():
    kb = FakeKeyboard()
    ms = FakeMouse()
    skill_keys = {"attack_single": "F1", "attack_aoe": "F2", "shield": "F3", "summon": "F4"}
    ex = ActionExecutor(kb, ms, skill_keys)

    ex.execute({"type": "use_skill", "skill": "attack_single", "target": {"x": 500, "y": 300}})
    assert "F1" in kb.pressed


def test_executor_use_hp_potion():
    kb = FakeKeyboard()
    ms = FakeMouse()
    ex = ActionExecutor(kb, ms, {}, hp_potion_key="1", mp_potion_key="2")

    ex.execute({"type": "use_hp_potion"})
    assert "1" in kb.pressed


def test_executor_use_mp_potion():
    kb = FakeKeyboard()
    ms = FakeMouse()
    ex = ActionExecutor(kb, ms, {}, hp_potion_key="1", mp_potion_key="2")

    ex.execute({"type": "use_mp_potion"})
    assert "2" in kb.pressed
