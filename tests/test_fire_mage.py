"""Tests for fire mage leveling strategy."""

import pytest

from src.strategy.fire_mage import build_fire_mage_fsm
from src.state.game import GameState
from src.state.player import PlayerState


def make_ctx(hp=1.0, mp=1.0, monsters=None, hp_threshold=0.5, mp_threshold=0.3):
    gs = GameState()
    gs.player.hp_ratio = hp
    gs.player.mp_ratio = mp
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.monsters = monsters or []
    return {
        "game_state": gs,
        "hp_threshold": hp_threshold,
        "mp_threshold": mp_threshold,
        "actions": [],
    }


def test_patrol_to_combat_on_monster():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.update(ctx)
    assert sm.current_state.name == "combat"


def test_patrol_stays_when_no_monster():
    sm = build_fire_mage_fsm()
    ctx = make_ctx()
    sm.update(ctx)
    assert sm.current_state.name == "patrol"


def test_combat_to_heal_when_low_hp():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.3, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("combat")
    sm.update(ctx)
    assert sm.current_state.name == "heal"


def test_combat_to_loot_when_no_monsters():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.8, monsters=[])
    sm.set_initial("combat")
    sm.update(ctx)
    assert sm.current_state.name == "loot"


def test_heal_to_combat_when_hp_ok():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.8, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("heal")
    sm.update(ctx)
    assert sm.current_state.name in ("patrol", "combat")
