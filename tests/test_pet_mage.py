"""Tests for pet mage leveling strategy."""

import pytest

from src.strategy.pet_mage import build_pet_mage_fsm
from src.state.game import GameState


def make_ctx(hp=1.0, mp=1.0, monsters=None, pet_alive=False,
             hp_threshold=0.5, mp_threshold=0.3, grid_pixels=48,
             hp_dropped=False):
    gs = GameState()
    gs.player.hp_ratio = hp
    gs.player.mp_ratio = mp
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.player.has_pet = pet_alive
    gs.pet_alive = pet_alive
    gs.monsters = monsters or []
    gs.hp_dropped = hp_dropped
    return {
        "game_state": gs,
        "hp_threshold": hp_threshold,
        "mp_threshold": mp_threshold,
        "grid_pixels": grid_pixels,
        "actions": [],
    }


def test_check_pet_summons_when_no_pet():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=False)
    sm.update(ctx)
    assert sm.current_state.name == "summon_pet"


def test_check_pet_to_patrol_when_pet_alive():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True)
    sm.update(ctx)
    assert sm.current_state.name == "patrol"


def test_patrol_to_approach_when_far_monster():
    """Monster far away (>5 grids) → approach."""
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 700, "y": 300, "type": "normal"}])
    sm.set_initial("patrol")
    sm.update(ctx)
    assert sm.current_state.name == "approach"


def test_patrol_to_evade_when_close_monster():
    """Monster close (<5 grids) → evade directly."""
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("patrol")
    sm.update(ctx)
    assert sm.current_state.name == "evade"


def test_evade_to_patrol_when_monsters_dead():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "patrol"


def test_evade_heal_when_low_hp():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(hp=0.3, pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "heal"


def test_evade_push_skill_on_hp_drop():
    """HP drops above 80% → F2 push skill."""
    sm = build_pet_mage_fsm()
    ctx = make_ctx(hp=0.9, pet_alive=True, hp_dropped=True,
                   monsters=[{"name": "鸡", "x": 410, "y": 310, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "evade"
    action_types = [a["type"] for a in ctx["actions"]]
    assert "push_skill" in action_types


def test_evade_escape_scroll_on_critical_hp_drop():
    """HP < 80% and still dropping → escape scroll."""
    sm = build_pet_mage_fsm()
    ctx = make_ctx(hp=0.7, pet_alive=True, hp_dropped=True,
                   monsters=[{"name": "鸡", "x": 410, "y": 310, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "evade"
    action_types = [a["type"] for a in ctx["actions"]]
    assert "escape_scroll" in action_types
