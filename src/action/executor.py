"""Translates strategy actions into keyboard/mouse operations."""

import math
import random
import time
from typing import Dict, List

from src.utils.logger import log


class ActionExecutor:
    """Executes actions by translating them to input events."""

    def __init__(self, keyboard, mouse, skill_keys: Dict[str, str],
                 hp_potion_key: str = "1", mp_potion_key: str = "2",
                 game_area: List[int] = None, safe_distance: int = 200):
        self.kb = keyboard
        self.mouse = mouse
        self.skill_keys = skill_keys
        self.hp_potion_key = hp_potion_key
        self.mp_potion_key = mp_potion_key
        self.game_area = game_area or [0, 0, 800, 600]
        self.safe_distance = safe_distance
        # Player is always at screen center in 传奇
        self.center_x = self.game_area[0] + self.game_area[2] // 2
        self.center_y = self.game_area[1] + self.game_area[3] // 2

    def execute(self, action: dict):
        """Execute a single action dict."""
        action_type = action.get("type")

        if action_type == "use_skill":
            self._use_skill(action)
        elif action_type == "use_hp_potion":
            self.kb.press_key(self.hp_potion_key)
        elif action_type == "use_mp_potion":
            self.kb.press_key(self.mp_potion_key)
        elif action_type == "loot_pickup":
            pass  # Not needed for pet mode
        elif action_type == "patrol_move":
            self._patrol_move(action)
        elif action_type == "pull_monsters":
            self._pull(action)
        elif action_type == "evade_monsters":
            self._evade(action)
        elif action_type == "revive":
            log.info("Reviving...")
        elif action_type == "go_town_buy":
            log.info("Going to town for resupply...")
        else:
            log.warning(f"Unknown action type: {action_type}")

    def _use_skill(self, action: dict):
        skill_name = action.get("skill", "")
        key = self.skill_keys.get(skill_name)
        if not key:
            log.warning(f"No key mapping for skill: {skill_name}")
            return

        target = action.get("target")
        if target:
            self.mouse.click(target["x"], target["y"])

        self.kb.press_key(key)
        log.debug(f"Used skill {skill_name} ({key})")

    def _patrol_move(self, action: dict):
        """Right-click a random position to wander around."""
        margin = 50
        x = random.randint(self.game_area[0] + margin, self.game_area[0] + self.game_area[2] - margin)
        y = random.randint(self.game_area[1] + margin, self.game_area[1] + self.game_area[3] - margin)
        self.mouse.click(x, y, button="right")
        log.debug(f"Patrol move -> ({x}, {y})")

    def _pull(self, action: dict):
        """Run toward monster then run back to pull it to pet."""
        target = action.get("target")
        if not target:
            return

        mx, my = target["x"], target["y"]

        # Step 1: Right-click toward the monster to approach
        self.mouse.click(mx, my, button="right")
        log.debug(f"Pull: running toward monster at ({mx}, {my})")

        # Step 2: Wait for character to approach
        time.sleep(1.0)

        # Step 3: Run back to screen center (where pet is)
        self.mouse.click(self.center_x, self.center_y, button="right")
        log.debug(f"Pull: running back to center ({self.center_x}, {self.center_y})")

    def _evade(self, action: dict):
        """Move away from monsters to let pet tank."""
        monsters = action.get("monsters", [])
        if not monsters:
            # No monster info, just move to a random edge
            self._patrol_move(action)
            return

        # Calculate centroid of all monsters
        avg_x = sum(m["x"] for m in monsters) / len(monsters)
        avg_y = sum(m["y"] for m in monsters) / len(monsters)

        # Direction away from monsters (from centroid toward player, extended)
        dx = self.center_x - avg_x
        dy = self.center_y - avg_y
        dist = math.hypot(dx, dy)

        if dist < 1:
            # Monsters right on top of us, pick random direction
            angle = random.uniform(0, 2 * math.pi)
            dx, dy = math.cos(angle), math.sin(angle)
            dist = 1.0

        # Normalize and extend to safe_distance from center
        scale = self.safe_distance / dist
        target_x = int(self.center_x + dx * scale)
        target_y = int(self.center_y + dy * scale)

        # Clamp within game area
        margin = 20
        target_x = max(self.game_area[0] + margin, min(target_x, self.game_area[0] + self.game_area[2] - margin))
        target_y = max(self.game_area[1] + margin, min(target_y, self.game_area[1] + self.game_area[3] - margin))

        self.mouse.click(target_x, target_y, button="right")
        log.debug(f"Evade -> ({target_x}, {target_y}), away from monsters at ({avg_x:.0f}, {avg_y:.0f})")

    def execute_all(self, actions: list):
        """Execute a list of actions."""
        for action in actions:
            self.execute(action)
