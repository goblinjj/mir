"""Tests for pet mage leveling strategy."""

import pytest

from src.strategy.pet_mage import build_pet_mage_fsm
from src.state.game import GameState


def make_ctx(hp=1.0, mp=1.0, monsters=None, pet_alive=False, hp_threshold=0.5, mp_threshold=0.3):
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
        "actions": [],
    }


def test_check_pet_summons_when_no_pet():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=False)
    sm.update(ctx)
    assert sm.current_state.name == "summon_pet"


def test_check_pet_to_pull_when_pet_alive():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True)
    sm.update(ctx)
    assert sm.current_state.name == "pull"


def test_pull_to_evade_when_monsters_found():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("pull")
    sm.update(ctx)
    assert sm.current_state.name == "evade"


def test_evade_to_loot_when_monsters_dead():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "loot"


def test_evade_heal_when_low_hp():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(hp=0.3, pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "heal"
