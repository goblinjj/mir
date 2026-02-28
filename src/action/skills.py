"""Skill management with cooldown tracking."""

import time
from typing import Dict, Optional


class SkillManager:
    """Manages skill key mappings and cooldowns."""

    def __init__(self, key_mapping: Dict[str, str]):
        self._keys = key_mapping
        self._last_used: Dict[str, float] = {}
        self._cooldowns: Dict[str, float] = {}

    def get_key(self, skill_name: str) -> Optional[str]:
        """Get the key binding for a skill."""
        return self._keys.get(skill_name)

    def use_skill(self, skill_name: str, cooldown: float = 0.0):
        """Record that a skill was used, setting its cooldown."""
        self._last_used[skill_name] = time.time()
        self._cooldowns[skill_name] = cooldown

    def is_ready(self, skill_name: str) -> bool:
        """Check if a skill is off cooldown."""
        if skill_name not in self._last_used:
            return True
        elapsed = time.time() - self._last_used[skill_name]
        cd = self._cooldowns.get(skill_name, 0.0)
        return elapsed >= cd
