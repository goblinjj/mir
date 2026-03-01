"""Pet mage leveling strategy — summon pet, patrol, approach, evade, escape."""

import math
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
            return "patrol"
        return "summon_pet"


class SummonPetState(State):
    name = "summon_pet"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "use_skill", "skill": "summon"})
        ctx["game_state"].pet_alive = True
        return "patrol"


class PatrolState(State):
    """Systematic directional patrol to explore the map."""
    name = "patrol"

    def __init__(self):
        self.direction = 0        # 0-7, rotates on stuck
        self.ticks_in_dir = 0     # how long we've been going this direction
        self.max_ticks_per_dir = 15  # switch direction after this many ticks even if not stuck

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"

        # Found monsters — decide approach or evade based on distance
        if gs.has_monsters():
            return self._check_monster_distance(ctx)

        # Stuck detection: rotate direction
        if gs.stuck_count >= 3:
            self.direction = (self.direction + 1) % 8
            self.ticks_in_dir = 0
            gs.stuck_count = 0
            log.info(f"Patrol: stuck, rotating to direction {self.direction}")

        # Also rotate after going in one direction too long
        self.ticks_in_dir += 1
        if self.ticks_in_dir > self.max_ticks_per_dir:
            self.direction = (self.direction + 1) % 8
            self.ticks_in_dir = 0

        ctx["actions"].append({"type": "patrol_move", "direction": self.direction})
        return None

    def _check_monster_distance(self, ctx: dict) -> str:
        gs = ctx["game_state"]
        grid_px = ctx.get("grid_pixels", 48)
        approach_dist = 5 * grid_px
        target = gs.nearest_monster()
        if target:
            dist = math.hypot(target["x"] - gs.player.screen_x, target["y"] - gs.player.screen_y)
            if dist > approach_dist:
                return "approach"
        return "evade"


class ApproachState(State):
    """Run toward monster until within evade distance."""
    name = "approach"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"
        if not gs.has_monsters():
            return "patrol"

        grid_px = ctx.get("grid_pixels", 48)
        evade_dist = 3 * grid_px
        target = gs.nearest_monster()

        if target:
            dist = math.hypot(target["x"] - gs.player.screen_x, target["y"] - gs.player.screen_y)
            if dist <= evade_dist:
                return "evade"
            ctx["actions"].append({"type": "approach_monster", "target": target})

        # Stuck while approaching — might be blocked
        if gs.stuck_count >= 5:
            return "surrounded"

        return None


class EvadeState(State):
    """Maintain safe distance from monsters, let pet tank."""
    name = "evade"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"
        if not gs.has_monsters():
            return "patrol"

        # Stuck while evading — surrounded
        if gs.stuck_count >= 3:
            return "surrounded"

        grid_px = ctx.get("grid_pixels", 48)
        evade_dist = 3 * grid_px
        target = gs.nearest_monster()

        if target:
            dist = math.hypot(target["x"] - gs.player.screen_x, target["y"] - gs.player.screen_y)
            if dist < evade_dist:
                # Monster too close, move away
                ctx["actions"].append({"type": "evade_monsters", "monsters": gs.monsters})

        # MP potion if needed
        if gs.player.needs_mp_potion(ctx["mp_threshold"]):
            ctx["actions"].append({"type": "use_mp_potion"})

        return None


class SurroundedState(State):
    """Stuck and surrounded — try to escape."""
    name = "surrounded"

    def __init__(self):
        self.attempts = 0

    def enter(self, ctx: dict):
        self.attempts = 0
        log.info("Surrounded! Attempting to escape...")

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"

        # If we managed to move, we're free
        if gs.stuck_count == 0:
            self.attempts = 0
            return "patrol"

        self.attempts += 1

        if self.attempts <= 2:
            # Try F2 push skill to knock back mobs
            ctx["actions"].append({"type": "push_skill"})
            # Then try to move away
            ctx["actions"].append({"type": "evade_monsters", "monsters": gs.monsters})
        elif self.attempts <= 4:
            # Still stuck, use random scroll to escape
            ctx["actions"].append({"type": "escape_scroll"})
            log.info("Using escape scroll!")
        else:
            # Reset and try again
            self.attempts = 0
            gs.stuck_count = 0

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
            return "patrol"
        return None


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
    sm.add_state(PatrolState())
    sm.add_state(ApproachState())
    sm.add_state(EvadeState())
    sm.add_state(SurroundedState())
    sm.add_state(PetHealState())
    sm.add_state(PetDeadState())
    sm.set_initial("check_pet")
    return sm
