"""Tests for pet mage leveling strategy."""

import numpy as np
import pytest

from src.strategy.pet_mage import build_pet_mage_fsm, PatrolState, ApproachState
from src.strategy.navigator import WaypointNavigator
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


def test_evade_stuck_uses_push_skill():
    """Stuck in evade (surrounded) → F2 push skill, reset stuck_count."""
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True,
                   monsters=[{"name": "鸡", "x": 410, "y": 310, "type": "normal"}])
    ctx["game_state"].stuck_count = 3
    sm.set_initial("evade")
    sm.update(ctx)
    action_types = [a["type"] for a in ctx["actions"]]
    assert "push_skill" in action_types
    assert ctx["game_state"].stuck_count == 0


def test_evade_to_approach_when_monster_far():
    """Monster moves far away (>5 grids) during evade → switch to approach."""
    sm = build_pet_mage_fsm()
    # Monster at 700,300 is far from player at 400,300 (300px > 5*48=240px)
    ctx = make_ctx(pet_alive=True,
                   monsters=[{"name": "鸡", "x": 700, "y": 300, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "approach"


class TestApproachWallStuck:
    """Tests for approach state wall-stuck sidestep logic."""

    def test_approach_sidesteps_when_stuck(self):
        """stuck_count >= 3 → sidestep perpendicular instead of straight approach."""
        state = ApproachState()
        ctx = make_ctx(pet_alive=True,
                       monsters=[{"name": "鸡", "x": 700, "y": 300, "type": "normal"}])
        ctx["game_state"].stuck_count = 3

        state.execute(ctx)

        # stuck_count should be reset
        assert ctx["game_state"].stuck_count == 0
        # Should have a sidestep action (target differs from monster position)
        assert len(ctx["actions"]) == 1
        target = ctx["actions"][0]["target"]
        # Sidestep target should NOT be at monster x=700
        assert target["x"] != 700 or target["y"] != 300

    def test_sidestep_lasts_multiple_ticks(self):
        """Sidestep continues for _SIDESTEP_TICKS before resuming normal approach."""
        state = ApproachState()
        monster = [{"name": "鸡", "x": 700, "y": 300, "type": "normal"}]

        # Trigger sidestep
        ctx = make_ctx(pet_alive=True, monsters=monster)
        ctx["game_state"].stuck_count = 3
        state.execute(ctx)

        # Next ticks should still sidestep (remaining = 2)
        for _ in range(ApproachState._SIDESTEP_TICKS - 1):
            ctx2 = make_ctx(pet_alive=True, monsters=monster)
            state.execute(ctx2)
            target = ctx2["actions"][0]["target"]
            assert target["x"] != 700 or target["y"] != 300

        # After sidestep exhausted, should approach monster directly
        ctx3 = make_ctx(pet_alive=True, monsters=monster)
        state.execute(ctx3)
        assert ctx3["actions"][0]["target"]["x"] == 700

    def test_sidestep_alternates_direction(self):
        """Each stuck event alternates sidestep direction."""
        state = ApproachState()
        monster = [{"name": "鸡", "x": 700, "y": 300, "type": "normal"}]

        # First stuck → sidestep direction A
        ctx1 = make_ctx(pet_alive=True, monsters=monster)
        ctx1["game_state"].stuck_count = 3
        state.execute(ctx1)
        first_y = ctx1["actions"][0]["target"]["y"]

        # Drain remaining ticks
        for _ in range(ApproachState._SIDESTEP_TICKS - 1):
            state.execute(make_ctx(pet_alive=True, monsters=monster))

        # Second stuck → sidestep direction B (opposite)
        ctx2 = make_ctx(pet_alive=True, monsters=monster)
        ctx2["game_state"].stuck_count = 3
        state.execute(ctx2)
        second_y = ctx2["actions"][0]["target"]["y"]

        # Perpendicular to (300,0) → y should go opposite directions
        assert first_y != second_y


def make_navigator(waypoints=None, arrival_radius=5):
    return WaypointNavigator(waypoints or [], arrival_radius=arrival_radius)


class TestPatrolWaypointNavigation:
    def test_patrol_uses_navigator_direction(self):
        """When navigator returns a direction, patrol uses it."""
        nav = make_navigator([[100, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (50, 50)  # player at (50,50), target at (100,50) = East
        state = PatrolState()
        result = state.execute(ctx)
        assert result is None  # stays in patrol
        actions = ctx["actions"]
        move_actions = [a for a in actions if a["type"] == "patrol_move"]
        assert len(move_actions) == 1
        assert move_actions[0]["direction"] == 2  # East

    def test_patrol_falls_back_to_rotation_without_navigator(self):
        """When no navigator or no minimap_pos, use old rotation logic."""
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = make_navigator()  # empty waypoints
        ctx["minimap_pos"] = None
        state = PatrolState()
        result = state.execute(ctx)
        assert result is None
        actions = ctx["actions"]
        move_actions = [a for a in actions if a["type"] == "patrol_move"]
        assert len(move_actions) == 1


class TestPatrolPathfinding:
    @staticmethod
    def _make_mask(width=160, height=180, walls=None):
        mask = np.ones((height, width), dtype=bool)
        if walls:
            for (x, y) in walls:
                mask[y, x] = False
        return mask

    def test_patrol_uses_bfs_path_with_mask(self):
        """When walkability_mask is provided, navigator plans a BFS path."""
        mask = self._make_mask()
        nav = make_navigator([[100, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (50, 50)
        ctx["walkability_mask"] = mask
        state = PatrolState()
        state.execute(ctx)
        # Navigator should have a path
        assert len(nav._path) > 0

    def test_patrol_stuck_forces_replan(self):
        """When stuck_count >= 3, force BFS replan and reset stuck_count."""
        mask = self._make_mask()
        nav = make_navigator([[100, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (50, 50)
        ctx["walkability_mask"] = mask
        ctx["game_state"].stuck_count = 5

        state = PatrolState()
        state.execute(ctx)

        # stuck_count should be reset
        assert ctx["game_state"].stuck_count == 0

    def test_patrol_works_without_mask(self):
        """Without walkability_mask, still works via straight-line fallback."""
        nav = make_navigator([[100, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (50, 50)
        # No walkability_mask in ctx
        state = PatrolState()
        state.execute(ctx)
        move = [a for a in ctx["actions"] if a["type"] == "patrol_move"][0]
        assert move["direction"] == 2  # East straight line


class TestPatrolTeleport:
    def test_teleport_resets_to_nearest_waypoint(self):
        """Large position jump triggers nearest waypoint search."""
        nav = make_navigator([[10, 10], [90, 90], [50, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (80, 80)  # close to waypoint[1] but outside arrival_radius
        state = PatrolState()
        state._last_pos = (10, 12)  # was near waypoint[0]
        state.execute(ctx)
        assert nav.current_index == 1  # jumped to nearest
