"""OCR-based monster detection."""

import os
# Must be set before paddle is imported anywhere
os.environ["FLAGS_use_mkldnn"] = "0"

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from src.utils.logger import log

DEFAULT_BOSS_NAMES = [
    "祖玛教主", "沃玛教主", "虹魔教主", "白野猪", "黑锷蜘蛛",
    "赤月恶魔", "触龙神", "骷髅精灵", "双头血魔", "牛魔王",
    "火龙神", "冰眼", "邪恶钳虫", "幻境迷宫",
]



@dataclass
class DetectedMonster:
    """A monster detected on screen."""
    name: str
    x: int
    y: int
    confidence: float


class MonsterDetector:
    """Detects monsters by OCR-reading their overhead names."""

    def __init__(self, boss_names: Optional[List[str]] = None,
                 monster_names: Optional[List[str]] = None):
        self.boss_names = boss_names or DEFAULT_BOSS_NAMES
        self.monster_names = monster_names or []
        self.ocr_engine = self._init_ocr()

    def _init_ocr(self):
        """Initialize PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR
            return PaddleOCR(use_angle_cls=False, lang="ch", show_log=False, enable_mkldnn=False)
        except Exception as e:
            log.warning("PaddleOCR unavailable (%s), using stub", e)
            return _StubOCR()

    def detect(self, frame: np.ndarray) -> List[DetectedMonster]:
        """Detect all monsters in the given frame."""
        if frame is None or frame.size == 0:
            log.debug("OCR: empty frame, skipping")
            return []

        try:
            results = self.ocr_engine.ocr(frame, cls=False)
        except Exception as e:
            log.error("OCR engine error: %s", e)
            return []

        monsters = []

        if not results or not results[0]:
            log.debug("OCR: no text detected in frame")
            return []

        all_texts = []
        for line in results[0]:
            bbox, (text, confidence) = line
            all_texts.append(f"{text.strip()}({confidence:.2f})")

            if confidence < 0.5:
                continue

            name = text.strip()
            if self.monster_names and not self._matches_whitelist(name):
                continue

            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            cx = int(sum(xs) / len(xs))
            cy = int(sum(ys) / len(ys))

            body_y = cy + 30

            monsters.append(DetectedMonster(
                name=name,
                x=cx,
                y=body_y,
                confidence=confidence,
            ))

        log.info("OCR raw: [%s] → matched %d monsters (whitelist=%s)",
                 ", ".join(all_texts), len(monsters), self.monster_names)

        return monsters

    def _matches_whitelist(self, name: str) -> bool:
        """Check if name matches any entry in the monster whitelist (substring)."""
        for wl in self.monster_names:
            if wl in name or name in wl:
                return True
        return False

    def classify(self, name: str) -> str:
        """Classify a monster by name. Returns 'boss' or 'normal'."""
        for boss in self.boss_names:
            if boss in name or name in boss:
                return "boss"
        return "normal"


class _StubOCR:
    """Stub OCR for environments without PaddleOCR."""

    def ocr(self, img, cls=False):
        return [[]]
