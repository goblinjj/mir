"""Pet mage leveling strategy — summon pet, pull mobs, evade."""

from typing import Optional

from src.strategy.base import State, StateMachine
from src.utils.logger import log


class CheckPetState(State):
    name = "check_pet"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.pet_alive:
            return "pull"
        return "summon_pet"


class SummonPetState(State):
    name = "summon_pet"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "use_skill", "skill": "summon"})
        ctx["game_state"].pet_alive = True
        return "pull"


class PullState(State):
    name = "pull"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"
        if gs.has_monsters():
            ctx["actions"].append({"type": "pull_monsters"})
            return "evade"
        ctx["actions"].append({"type": "patrol_move"})
        return None


class EvadeState(State):
    name = "evade"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"
        if not gs.pet_alive:
            return "check_pet"
        if not gs.has_monsters():
            return "loot"
        ctx["actions"].append({"type": "evade_monsters"})
        if gs.player.needs_mp_potion(ctx["mp_threshold"]):
            ctx["actions"].append({"type": "use_mp_potion"})
        return None


class PetHealState(State):
    name = "heal"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.has_monsters():
            ctx["actions"].append({"type": "use_skill", "skill": "shield"})
        ctx["actions"].append({"type": "use_hp_potion"})
        if not gs.player.needs_hp_potion(ctx["hp_threshold"]):
            if gs.has_monsters():
                return "evade"
            return "pull"
        return None


class PetLootState(State):
    name = "loot"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "loot_pickup"})
        return "pull"


class PetDeadState(State):
    name = "dead"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if not gs.player.is_dead:
            return "check_pet"
        ctx["actions"].append({"type": "revive"})
        return None


def build_pet_mage_fsm() -> StateMachine:
    """Build and return the pet mage strategy state machine."""
    sm = StateMachine()
    sm.add_state(CheckPetState())
    sm.add_state(SummonPetState())
    sm.add_state(PullState())
    sm.add_state(EvadeState())
    sm.add_state(PetHealState())
    sm.add_state(PetLootState())
    sm.add_state(PetDeadState())
    sm.set_initial("check_pet")
    return sm
