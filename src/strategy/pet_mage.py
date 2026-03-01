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
    """Patrol state: navigate between waypoints or fall back to rotation."""
    name = "patrol"

    def __init__(self):
        # Fallback rotation fields (used when no waypoints)
        self.direction = 0
        self.ticks_in_dir = 0
        self.max_ticks_per_dir = 15
        # Teleport detection
        self._last_pos = None
        self._teleport_threshold = 30  # pixels on minimap

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

        # Determine move direction
        navigator = ctx.get("navigator")
        minimap_pos = ctx.get("minimap_pos")
        direction = None

        if navigator and minimap_pos and navigator.waypoints:
            # Teleport detection
            if self._last_pos is not None:
                jump_dist = math.hypot(
                    minimap_pos[0] - self._last_pos[0],
                    minimap_pos[1] - self._last_pos[1],
                )
                if jump_dist > self._teleport_threshold:
                    navigator.handle_teleport(minimap_pos)
                    log.info("Patrol: teleport detected, jumping to waypoint %d",
                             navigator.current_index)
            self._last_pos = minimap_pos
            direction = navigator.get_direction(minimap_pos)

        if direction is None:
            # Fallback: old rotation logic
            direction = self._rotation_direction(gs)

        ctx["actions"].append({"type": "patrol_move", "direction": direction})
        return None

    def _rotation_direction(self, gs) -> int:
        """Fallback direction rotation when no waypoints."""
        if gs.stuck_count >= 3:
            self.direction = (self.direction + 1) % 8
            self.ticks_in_dir = 0
            gs.stuck_count = 0
            log.info("Patrol: stuck, rotating to direction %d", self.direction)

        self.ticks_in_dir += 1
        if self.ticks_in_dir > self.max_ticks_per_dir:
            self.direction = (self.direction + 1) % 8
            self.ticks_in_dir = 0

        return self.direction

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

        return None


class EvadeState(State):
    """Maintain safe distance from monsters, let pet tank.

    Emergency reactions based on HP drops:
    - HP drops (被打了) → F2 push skill + evade
    - HP < 80% and drops again → key 1 escape scroll
    """
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

        # Emergency: HP dropped (being hit)
        if gs.hp_dropped:
            if gs.player.hp_ratio < 0.8:
                # HP < 80% and still dropping → escape with scroll
                ctx["actions"].append({"type": "escape_scroll"})
                log.info("HP critical and dropping! Using escape scroll")
                return None
            else:
                # HP dropped but still above 80% → F2 push + evade
                ctx["actions"].append({"type": "push_skill"})
                log.info("HP dropped! Using push skill (F2)")

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
    sm.add_state(PetHealState())
    sm.add_state(PetDeadState())
    sm.set_initial("check_pet")
    return sm
