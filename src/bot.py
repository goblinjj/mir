"""Main bot loop — ties all modules together."""

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
        self.monster_detector = MonsterDetector()

        self.keyboard = KeyboardSim()
        self.mouse = MouseSim()

        skill_keys = {
            "attack_single": self.config.skills.attack_single,
            "attack_aoe": self.config.skills.attack_aoe,
            "shield": self.config.skills.shield,
            "summon": self.config.skills.summon,
            "boss_skill": self.config.skills.boss_skill,
        }
        self.executor = ActionExecutor(self.keyboard, self.mouse, skill_keys)

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

        ctx = {
            "game_state": self.game_state,
            "hp_threshold": self.config.player.hp_threshold,
            "mp_threshold": self.config.player.mp_threshold,
            "actions": [],
        }
        self.strategy.update(ctx)

        self.executor.execute_all(ctx["actions"])

    def _update_state(self, frame: np.ndarray):
        """Update game state from a captured frame."""
        hp_ratio, mp_ratio = self.hp_mp.detect_hp_mp(
            frame,
            self.config.screen.hp_text_region,
            self.config.screen.mp_text_region,
        )
        self.game_state.player.hp_ratio = hp_ratio
        self.game_state.player.mp_ratio = mp_ratio

        detected = self.monster_detector.detect(frame)
        self.game_state.monsters = [
            {"name": m.name, "x": m.x, "y": m.y, "type": self.monster_detector.classify(m.name)}
            for m in detected
        ]

    def set_mode(self, mode: str):
        """Switch leveling mode ('fire' or 'pet')."""
        if mode == "pet":
            self.strategy = build_pet_mage_fsm()
        else:
            self.strategy = build_fire_mage_fsm()
        self.config.leveling.mode = mode
        log.info(f"Switched to {mode} mode")
