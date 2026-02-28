"""Player state tracking."""

from dataclasses import dataclass


@dataclass
class PlayerState:
    """Tracks the player's current state."""
    hp_ratio: float = 1.0
    mp_ratio: float = 1.0
    screen_x: int = 0
    screen_y: int = 0
    level: int = 0
    has_pet: bool = False

    @property
    def is_dead(self) -> bool:
        return self.hp_ratio <= 0.0

    def needs_hp_potion(self, threshold: float) -> bool:
        return self.hp_ratio < threshold

    def needs_mp_potion(self, threshold: float) -> bool:
        return self.mp_ratio < threshold
