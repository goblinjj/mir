"""Fire mage leveling strategy — state machine states."""

from typing import Optional

from src.strategy.base import State, StateMachine
from src.utils.logger import log


class PatrolState(State):
    name = "patrol"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.has_monsters():
            return "combat"
        ctx["actions"].append({"type": "patrol_move"})
        return None


class CombatState(State):
    name = "combat"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"
        if not gs.has_monsters():
            return "loot"
        if gs.player.needs_mp_potion(ctx["mp_threshold"]):
            ctx["actions"].append({"type": "use_mp_potion"})
        target = gs.nearest_monster()
        if gs.monster_count() >= 3:
            ctx["actions"].append({"type": "use_skill", "skill": "attack_aoe", "target": target})
        else:
            ctx["actions"].append({"type": "use_skill", "skill": "attack_single", "target": target})
        return None


class HealState(State):
    name = "heal"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.has_monsters():
            ctx["actions"].append({"type": "use_skill", "skill": "shield"})
        ctx["actions"].append({"type": "use_hp_potion"})
        if not gs.player.needs_hp_potion(ctx["hp_threshold"]):
            if gs.has_monsters():
                return "combat"
            return "patrol"
        return None


class LootState(State):
    name = "loot"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        ctx["actions"].append({"type": "loot_pickup"})
        return "patrol"


class DeadState(State):
    name = "dead"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if not gs.player.is_dead:
            return "patrol"
        ctx["actions"].append({"type": "revive"})
        return None


class ResupplyState(State):
    name = "resupply"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "go_town_buy"})
        return "patrol"


def build_fire_mage_fsm() -> StateMachine:
    """Build and return the fire mage strategy state machine."""
    sm = StateMachine()
    sm.add_state(PatrolState())
    sm.add_state(CombatState())
    sm.add_state(HealState())
    sm.add_state(LootState())
    sm.add_state(DeadState())
    sm.add_state(ResupplyState())
    sm.set_initial("patrol")
    return sm
