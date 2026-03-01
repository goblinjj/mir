"""Tests for pet mage leveling strategy."""

import pytest

from src.strategy.pet_mage import build_pet_mage_fsm
from src.state.game import GameState


def make_ctx(hp=1.0, mp=1.0, monsters=None, pet_alive=False,
             hp_threshold=0.5, mp_threshold=0.3, grid_pixels=48):
    gs = GameState()
    gs.player.hp_ratio = hp
    gs.player.mp_ratio = mp
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.player.has_pet = pet_alive
    gs.pet_alive = pet_alive
    gs.monsters = monsters or []
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
    # Monster at (700, 300), player at (400, 300), dist=300px > 5*48=240
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 700, "y": 300, "type": "normal"}])
    sm.set_initial("patrol")
    sm.update(ctx)
    assert sm.current_state.name == "approach"


def test_patrol_to_evade_when_close_monster():
    """Monster close (<5 grids) → evade directly."""
    sm = build_pet_mage_fsm()
    # Monster at (450, 320), player at (400, 300), dist=~54px < 240
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


def test_surrounded_when_stuck():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 410, "y": 310, "type": "normal"}])
    ctx["game_state"].stuck_count = 5
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "surrounded"


def test_surrounded_escape_when_unstuck():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True)
    ctx["game_state"].stuck_count = 0
    sm.set_initial("surrounded")
    sm.update(ctx)
    assert sm.current_state.name == "patrol"
