"""Main bot loop — ties all modules together."""

import re
import time
from typing import Optional

from src.utils.config import Config, load_config
from src.utils.logger import log
from src.capture.window import GameWindow
from src.capture.screen import ScreenCapture
from src.vision.hp_mp import HpMpDetector
from src.vision.ocr import MonsterDetector
from src.state.game import GameState
from src.action.keyboard import KeyboardSim
from src.action.mouse import MouseSim
from src.action.executor import ActionExecutor
from src.strategy.fire_mage import build_fire_mage_fsm
from src.strategy.pet_mage import build_pet_mage_fsm
from src.vision.minimap import MinimapAnalyzer
from src.strategy.navigator import WaypointNavigator

import numpy as np


class MirBot:
    """Main bot orchestrator."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.running = False
        self.game_state = GameState()

        # Modules
        self.window = GameWindow(self.config.game.window_title)
        self.screen = ScreenCapture()
        self.hp_mp = HpMpDetector()
        self.monster_detector = MonsterDetector(
            monster_names=self.config.leveling.monster_names,
        )

        self.keyboard = KeyboardSim()
        self.mouse = MouseSim()

        skill_keys = {
            "attack_single": self.config.skills.attack_single,
            "attack_aoe": self.config.skills.attack_aoe,
            "shield": self.config.skills.shield,
            "summon": self.config.skills.summon,
            "boss_skill": self.config.skills.boss_skill,
        }
        self.executor = ActionExecutor(
            self.keyboard, self.mouse, skill_keys,
            game_area=self.config.screen.game_area,
            safe_distance=self.config.pet.safe_distance,
        )

        # Minimap analyzer
        self.minimap_region = self.config.minimap.region  # [x, y, w, h]
        self.minimap_analyzer = MinimapAnalyzer(
            white_threshold=self.config.minimap.white_threshold,
            black_threshold=self.config.minimap.black_threshold,
        )
        self.navigator = WaypointNavigator(
            waypoints=self.config.patrol.waypoints,
            arrival_radius=self.config.minimap.arrival_radius,
        )
        self._last_minimap_pos = None
        self.last_minimap_frame = None

        # Strategy
        if self.config.leveling.mode == "pet":
            self.strategy = build_pet_mage_fsm()
        else:
            self.strategy = build_fire_mage_fsm()

        log.info(f"Bot initialized, mode={self.config.leveling.mode}")

    def start(self):
        """Start the bot main loop."""
        if not self.window.find_window():
            log.error("Cannot find game window. Is the game running?")
            return

        self.keyboard.hwnd = self.window.hwnd
        self.mouse.hwnd = self.window.hwnd
        self.running = True
        log.info("Bot started")

        try:
            while self.running:
                self._tick()
                time.sleep(0.1)
        except KeyboardInterrupt:
            log.info("Bot stopped by user")
        finally:
            self.running = False

    def stop(self):
        """Stop the bot."""
        self.running = False
        log.info("Bot stopping...")

    def _tick(self):
        """One iteration of the bot loop."""
        frame = self.screen.capture(self.window.hwnd)
        if frame is None:
            return

        try:
            self._update_state(frame)
        except Exception as e:
            log.error("Failed to update state: %s", e)
            return

        # Minimap player detection and walkability
        minimap_pos = self._detect_minimap_position(frame)
        if minimap_pos:
            self._last_minimap_pos = minimap_pos

        walkability_mask = None
        raw_mask = None
        if self.last_minimap_frame is not None:
            raw_mask = self.minimap_analyzer.get_walkability_mask(
                self.last_minimap_frame
            )
            walkability_mask = self.minimap_analyzer.get_walkability_mask(
                self.last_minimap_frame, erode=4
            )

        ctx = {
            "game_state": self.game_state,
            "hp_threshold": self.config.player.hp_threshold,
            "mp_threshold": self.config.player.mp_threshold,
            "grid_pixels": self.config.pet.grid_pixels,
            "actions": [],
            "navigator": self.navigator,
            "minimap_pos": self._last_minimap_pos,
            "walkability_mask": walkability_mask,
            "raw_mask": raw_mask,
        }
        self.strategy.update(ctx)

        try:
            self.executor.execute_all(ctx["actions"])
        except Exception as e:
            log.error("Failed to execute actions: %s", e)

    def _detect_minimap_position(self, frame):
        """Crop minimap region and detect player white dot."""
        x, y, w, h = self.minimap_region
        if w <= 0 or h <= 0:
            return None
        minimap = frame[y:y+h, x:x+w]
        self.last_minimap_frame = minimap
        return self.minimap_analyzer.detect_player_position(minimap)

    def _update_state(self, frame: np.ndarray):
        """Update game state from a captured frame."""
        hp_ratio, mp_ratio = self.hp_mp.detect_hp_mp(
            frame,
            self.config.screen.hp_text_region,
            self.config.screen.mp_text_region,
        )
        # Detect HP drop (compared to last frame)
        self.game_state.hp_dropped = hp_ratio < self.game_state.last_hp_ratio
        self.game_state.last_hp_ratio = hp_ratio
        self.game_state.player.hp_ratio = hp_ratio
        self.game_state.player.mp_ratio = mp_ratio
        # Player is always at screen center in 传奇
        ga = self.config.screen.game_area
        self.game_state.player.screen_x = ga[0] + ga[2] // 2
        self.game_state.player.screen_y = ga[1] + ga[3] // 2

        detected = self.monster_detector.detect(frame)
        self.game_state.monsters = [
            {"name": m.name, "x": m.x, "y": m.y, "type": self.monster_detector.classify(m.name)}
            for m in detected
        ]
        if detected:
            names = [m.name for m in detected]
            log.info(f"OCR detected: {names}")

        # Read map coordinates for movement detection
        coord_region = self.config.screen.coord_text_region
        if coord_region[2] > 0 and coord_region[3] > 0:
            self._update_coordinates(frame, coord_region)

    _COORD_PATTERN = re.compile(r"(\d+)\D+(\d+)")

    def _update_coordinates(self, frame: np.ndarray, region: list):
        """Read map coordinates from screen and detect stuck state."""
        coord_img = frame[region[1]:region[1]+region[3], region[0]:region[0]+region[2]]
        if coord_img.size == 0 or self.hp_mp.ocr is None:
            return

        try:
            text = self.hp_mp.ocr.read_text(coord_img)
            match = self._COORD_PATTERN.search(text)
            if not match:
                return

            new_x, new_y = int(match.group(1)), int(match.group(2))
            old_x, old_y = self.game_state.player.map_x, self.game_state.player.map_y

            if old_x >= 0 and old_y >= 0:
                if new_x == old_x and new_y == old_y:
                    self.game_state.stuck_count += 1
                else:
                    self.game_state.stuck_count = 0

            self.game_state.player.map_x = new_x
            self.game_state.player.map_y = new_y
        except Exception:
            pass

    def set_mode(self, mode: str):
        """Switch leveling mode ('fire' or 'pet')."""
        if mode == "pet":
            self.strategy = build_pet_mage_fsm()
        else:
            self.strategy = build_fire_mage_fsm()
        self.config.leveling.mode = mode
        log.info(f"Switched to {mode} mode")
