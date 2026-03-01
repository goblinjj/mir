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
        walkability_mask = ctx.get("walkability_mask")
        raw_mask = ctx.get("raw_mask")
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

            # BFS path planning (replan when stuck or path invalid)
            force_replan = gs.stuck_count >= 3
            navigator.update_path(minimap_pos, walkability_mask,
                                  raw_mask=raw_mask, force=force_replan)
            if force_replan:
                gs.stuck_count = 0

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
    """Run toward monster until within evade distance.

    Wall-stuck detection: if stuck_count >= 3 (coordinates unchanged),
    sidestep perpendicular to the monster direction for a few ticks,
    then resume approaching.
    """
    name = "approach"
    _SIDESTEP_TICKS = 3

    def __init__(self):
        self._sidestep_remaining = 0
        self._sidestep_dir = 1  # +1 or -1 (clockwise / counter-clockwise)

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

        if not target:
            return None

        dist = math.hypot(target["x"] - gs.player.screen_x,
                          target["y"] - gs.player.screen_y)
        if dist <= evade_dist:
            return "evade"

        # Wall-stuck: coordinates haven't changed for several ticks
        if gs.stuck_count >= 3 and self._sidestep_remaining <= 0:
            self._sidestep_remaining = self._SIDESTEP_TICKS
            self._sidestep_dir *= -1  # alternate direction each time
            gs.stuck_count = 0
            log.info("Approach: wall stuck, sidestepping")

        if self._sidestep_remaining > 0:
            # Move perpendicular to monster direction
            dx = target["x"] - gs.player.screen_x
            dy = target["y"] - gs.player.screen_y
            # Rotate 90°: (dx,dy) → (-dy,dx) or (dy,-dx)
            perp_x = -dy * self._sidestep_dir
            perp_y = dx * self._sidestep_dir
            length = math.hypot(perp_x, perp_y)
            if length > 0:
                perp_x, perp_y = perp_x / length, perp_y / length
            step_dist = 200
            sidestep_target = {
                "x": int(gs.player.screen_x + perp_x * step_dist),
                "y": int(gs.player.screen_y + perp_y * step_dist),
            }
            ctx["actions"].append({"type": "approach_monster", "target": sidestep_target})
            self._sidestep_remaining -= 1
        else:
            ctx["actions"].append({"type": "approach_monster", "target": target})

        return None


class EvadeState(State):
    """Maintain safe distance from monsters, let pet tank.

    - Continuously checks nearest monster distance:
      - Too close (< 3 grids) → evade away
      - Far enough (> 5 grids) → switch to approach
    - Stuck detection: if coordinates don't change (stuck_count >= 3),
      use F2 push skill to break free
    - HP drops → F2 push; HP < 80% and drops → escape scroll
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

        grid_px = ctx.get("grid_pixels", 48)
        evade_dist = 3 * grid_px
        approach_dist = 5 * grid_px
        target = gs.nearest_monster()

        # Emergency: HP dropped (being hit)
        if gs.hp_dropped:
            if gs.player.hp_ratio < 0.8:
                ctx["actions"].append({"type": "escape_scroll"})
                log.info("HP critical and dropping! Using escape scroll")
                return None
            else:
                ctx["actions"].append({"type": "push_skill"})
                log.info("HP dropped! Using push skill (F2)")

        # Stuck detection: coordinates not changing → surrounded, use F2
        if gs.stuck_count >= 3:
            ctx["actions"].append({"type": "push_skill"})
            gs.stuck_count = 0
            log.info("Evade: stuck (surrounded), using push skill (F2)")

        # Distance-based decisions on nearest monster
        if target:
            dist = math.hypot(target["x"] - gs.player.screen_x,
                              target["y"] - gs.player.screen_y)
            if dist > approach_dist:
                # Monster far away, switch to approach
                return "approach"
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
