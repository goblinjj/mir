"""Tests for action modules (platform-independent logic)."""

import pytest

from src.action.skills import SkillManager


def test_skill_manager_init():
    keys = {
        "attack_single": "F1",
        "attack_aoe": "F2",
        "shield": "F3",
        "summon": "F4",
        "boss_skill": "F5",
    }
    sm = SkillManager(keys)
    assert sm.get_key("attack_single") == "F1"
    assert sm.get_key("shield") == "F3"


def test_skill_manager_unknown_skill():
    sm = SkillManager({"attack_single": "F1"})
    assert sm.get_key("nonexistent") is None


def test_skill_cooldown():
    sm = SkillManager({"attack_single": "F1"})
    assert sm.is_ready("attack_single") is True
    sm.use_skill("attack_single", cooldown=1.0)
    assert sm.is_ready("attack_single") is False
