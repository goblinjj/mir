"""Tests for strategy state machine base."""

import pytest

from src.strategy.base import StateMachine, State


class IdleState(State):
    name = "idle"

    def enter(self, ctx):
        ctx["entered_idle"] = True

    def execute(self, ctx):
        if ctx.get("start_fight"):
            return "fight"
        return None

    def exit(self, ctx):
        ctx["exited_idle"] = True


class FightState(State):
    name = "fight"

    def execute(self, ctx):
        ctx["fighting"] = True
        return "idle"


def test_state_machine_transitions():
    sm = StateMachine()
    sm.add_state(IdleState())
    sm.add_state(FightState())
    sm.set_initial("idle")

    ctx = {}
    sm.update(ctx)  # idle.execute -> stays idle
    assert ctx.get("entered_idle") is True

    ctx["start_fight"] = True
    sm.update(ctx)  # idle.execute -> returns "fight"
    assert ctx.get("exited_idle") is True
    assert sm.current_state.name == "fight"

    sm.update(ctx)  # fight.execute -> returns "idle"
    assert ctx.get("fighting") is True
    assert sm.current_state.name == "idle"
