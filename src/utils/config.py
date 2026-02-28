"""Configuration loader for MirBot."""

from dataclasses import dataclass, field
from typing import List, Tuple

import yaml


@dataclass
class GameConfig:
    window_title: str = "热血传奇"


@dataclass
class PlayerConfig:
    hp_threshold: float = 0.5
    mp_threshold: float = 0.3
    potion_min_count: int = 5


@dataclass
class SkillsConfig:
    attack_single: str = "F1"
    attack_aoe: str = "F2"
    shield: str = "F3"
    summon: str = "F4"
    boss_skill: str = "F5"


@dataclass
class LevelingConfig:
    mode: str = "fire"
    patrol_points: List[List[int]] = field(default_factory=list)
    loot_enabled: bool = True
    loot_filter: List[str] = field(default_factory=list)


@dataclass
class PetConfig:
    pull_count: int = 3
    safe_distance: int = 200


@dataclass
class ScreenConfig:
    hp_bar_region: List[int] = field(default_factory=lambda: [10, 40, 160, 52])
    mp_bar_region: List[int] = field(default_factory=lambda: [10, 56, 160, 68])
    game_area: List[int] = field(default_factory=lambda: [0, 0, 800, 600])


@dataclass
class ColorsConfig:
    hp_red: List[int] = field(default_factory=lambda: [180, 0, 0])
    hp_red_max: List[int] = field(default_factory=lambda: [255, 80, 80])
    mp_blue: List[int] = field(default_factory=lambda: [0, 0, 180])
    mp_blue_max: List[int] = field(default_factory=lambda: [80, 80, 255])


@dataclass
class Config:
    game: GameConfig = field(default_factory=GameConfig)
    player: PlayerConfig = field(default_factory=PlayerConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    leveling: LevelingConfig = field(default_factory=LevelingConfig)
    pet: PetConfig = field(default_factory=PetConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    colors: ColorsConfig = field(default_factory=ColorsConfig)


def _dict_to_dataclass(cls, data: dict):
    """Convert a dict to a dataclass, ignoring unknown keys."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def load_config(path: str) -> Config:
    """Load config from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Config(
        game=_dict_to_dataclass(GameConfig, raw.get("game", {})),
        player=_dict_to_dataclass(PlayerConfig, raw.get("player", {})),
        skills=_dict_to_dataclass(SkillsConfig, raw.get("skills", {})),
        leveling=_dict_to_dataclass(LevelingConfig, raw.get("leveling", {})),
        pet=_dict_to_dataclass(PetConfig, raw.get("pet", {})),
        screen=_dict_to_dataclass(ScreenConfig, raw.get("screen", {})),
        colors=_dict_to_dataclass(ColorsConfig, raw.get("colors", {})),
    )
