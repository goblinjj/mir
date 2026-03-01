"""OCR-based monster detection."""

import os
# Must be set before paddle is imported anywhere
os.environ["FLAGS_use_mkldnn"] = "0"

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

from src.utils.logger import log

# Preprocessing constants
_WHITE_THRESH = 200       # Min per-channel value to count as "white" text
_SCALE_FACTOR = 2         # Upscale ratio for small text
_BINARY_THRESH = 150      # Grayscale threshold for binarization
_MORPH_KERNEL_SIZE = 2    # Kernel size for morphological closing

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

    @staticmethod
    def preprocess_frame(frame: np.ndarray) -> np.ndarray:
        """Preprocess game frame to isolate white monster name text.

        Pipeline: white-pixel filter → 2x upscale → grayscale → binarize → invert → morphological close.
        Returns a clean black-text-on-white image optimized for OCR.
        Falls back to returning the original frame if cv2 is unavailable.
        """
        if not _HAS_CV2:
            return frame

        # 1. White text filter: keep pixels where all channels > threshold
        if len(frame.shape) == 3:
            mask = np.all(frame > _WHITE_THRESH, axis=2)
            filtered = np.zeros_like(frame)
            filtered[mask] = frame[mask]
        else:
            filtered = frame.copy()
            filtered[filtered <= _WHITE_THRESH] = 0

        # 2. Upscale for small text
        h, w = filtered.shape[:2]
        scaled = cv2.resize(filtered, (w * _SCALE_FACTOR, h * _SCALE_FACTOR),
                            interpolation=cv2.INTER_CUBIC)

        # 3. Grayscale (use max channel to catch white text)
        if len(scaled.shape) == 3:
            gray = np.max(scaled, axis=2).astype(np.uint8)
        else:
            gray = scaled

        # 4. Binary threshold + invert (black text on white background)
        _, binary = cv2.threshold(gray, _BINARY_THRESH, 255, cv2.THRESH_BINARY)
        inverted = cv2.bitwise_not(binary)

        # 5. Morphological closing to connect broken strokes
        kernel = np.ones((_MORPH_KERNEL_SIZE, _MORPH_KERNEL_SIZE), np.uint8)
        closed = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel)

        return closed

    def detect(self, frame: np.ndarray) -> List[DetectedMonster]:
        """Detect all monsters in the given frame."""
        if frame is None or frame.size == 0:
            log.debug("OCR: empty frame, skipping")
            return []

        processed = self.preprocess_frame(frame)

        try:
            results = self.ocr_engine.ocr(processed, cls=False)
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
            if not self.monster_names or not self._matches_whitelist(name):
                continue

            # Scale coordinates back to original frame size
            xs = [p[0] / _SCALE_FACTOR for p in bbox]
            ys = [p[1] / _SCALE_FACTOR for p in bbox]
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
