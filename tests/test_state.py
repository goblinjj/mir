"""Tests for game state management."""

import pytest

from src.state.player import PlayerState
from src.state.game import GameState


def test_player_state_init():
    ps = PlayerState()
    assert ps.hp_ratio == 1.0
    assert ps.mp_ratio == 1.0
    assert ps.is_dead is False


def test_player_needs_hp_potion():
    ps = PlayerState()
    ps.hp_ratio = 0.3
    assert ps.needs_hp_potion(threshold=0.5) is True
    ps.hp_ratio = 0.7
    assert ps.needs_hp_potion(threshold=0.5) is False


def test_player_needs_mp_potion():
    ps = PlayerState()
    ps.mp_ratio = 0.2
    assert ps.needs_mp_potion(threshold=0.3) is True


def test_player_is_dead():
    ps = PlayerState()
    ps.hp_ratio = 0.0
    assert ps.is_dead is True


def test_game_state_init():
    gs = GameState()
    assert gs.player is not None
    assert gs.monsters == []
    assert gs.current_map == ""


def test_game_state_has_monsters():
    gs = GameState()
    assert gs.has_monsters() is False
    gs.monsters = [{"name": "鸡", "x": 100, "y": 200}]
    assert gs.has_monsters() is True


def test_game_state_nearest_monster():
    gs = GameState()
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.monsters = [
        {"name": "鸡", "x": 500, "y": 300},
        {"name": "鹿", "x": 410, "y": 310},
    ]
    nearest = gs.nearest_monster()
    assert nearest["name"] == "鹿"
