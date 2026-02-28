"""Game state aggregation."""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from src.state.player import PlayerState


@dataclass
class GameState:
    """Aggregated game state."""
    player: PlayerState = field(default_factory=PlayerState)
    monsters: List[Dict] = field(default_factory=list)
    current_map: str = ""
    pet_alive: bool = False

    def has_monsters(self) -> bool:
        return len(self.monsters) > 0

    def nearest_monster(self) -> Optional[Dict]:
        """Find the nearest monster to the player."""
        if not self.monsters:
            return None

        px, py = self.player.screen_x, self.player.screen_y

        def distance(m):
            return math.hypot(m["x"] - px, m["y"] - py)

        return min(self.monsters, key=distance)

    def monster_count(self) -> int:
        return len(self.monsters)
