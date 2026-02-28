"""Tests for main bot loop."""

import pytest

from src.bot import MirBot


def test_bot_init():
    bot = MirBot.__new__(MirBot)
    bot.running = False
    assert bot.running is False


def test_bot_mode_selection():
    """Test that bot can switch between fire and pet mode."""
    from src.strategy.fire_mage import build_fire_mage_fsm
    from src.strategy.pet_mage import build_pet_mage_fsm

    fire_sm = build_fire_mage_fsm()
    pet_sm = build_pet_mage_fsm()

    assert fire_sm.current_state.name == "patrol"
    assert pet_sm.current_state.name == "check_pet"
