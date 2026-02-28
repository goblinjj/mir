import os
import tempfile

import yaml
import pytest

from src.utils.config import load_config, Config


def test_load_config_from_file():
    data = {
        "game": {"window_title": "测试传奇"},
        "player": {"hp_threshold": 0.6, "mp_threshold": 0.4, "potion_min_count": 10},
        "skills": {"attack_single": "F1", "attack_aoe": "F2", "shield": "F3", "summon": "F4", "boss_skill": "F5"},
        "leveling": {"mode": "fire", "patrol_points": [], "loot_enabled": True, "loot_filter": []},
        "pet": {"pull_count": 3, "safe_distance": 200},
        "screen": {
            "hp_bar_region": [10, 40, 160, 52],
            "mp_bar_region": [10, 56, 160, 68],
            "game_area": [0, 0, 800, 600],
        },
        "colors": {
            "hp_red": [180, 0, 0], "hp_red_max": [255, 80, 80],
            "mp_blue": [0, 0, 180], "mp_blue_max": [80, 80, 255],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        path = f.name
    try:
        config = load_config(path)
        assert isinstance(config, Config)
        assert config.game.window_title == "测试传奇"
        assert config.player.hp_threshold == 0.6
        assert config.leveling.mode == "fire"
    finally:
        os.unlink(path)


def test_load_default_config():
    config = load_config("config.yaml")
    assert config.player.hp_threshold == 0.5
    assert config.player.mp_threshold == 0.3
