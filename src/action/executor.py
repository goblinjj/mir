"""Translates strategy actions into keyboard/mouse operations."""

from typing import Dict, Optional

from src.utils.logger import log


class ActionExecutor:
    """Executes actions by translating them to input events."""

    def __init__(self, keyboard, mouse, skill_keys: Dict[str, str],
                 hp_potion_key: str = "1", mp_potion_key: str = "2"):
        self.kb = keyboard
        self.mouse = mouse
        self.skill_keys = skill_keys
        self.hp_potion_key = hp_potion_key
        self.mp_potion_key = mp_potion_key

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
            self._loot(action)
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

    def _loot(self, action: dict):
        log.debug("Picking up loot")

    def _patrol_move(self, action: dict):
        log.debug("Patrol move")

    def _pull(self, action: dict):
        log.debug("Pulling monsters towards pet")

    def _evade(self, action: dict):
        log.debug("Evading monsters")

    def execute_all(self, actions: list):
        """Execute a list of actions."""
        for action in actions:
            self.execute(action)
