"""HP and MP bar detection using color ratio analysis."""

import numpy as np

from src.utils.logger import log


class HpMpDetector:
    """Detects HP/MP percentage by analyzing color distribution in bar regions."""

    def __init__(
        self,
        hp_color_min: np.ndarray,
        hp_color_max: np.ndarray,
        mp_color_min: np.ndarray,
        mp_color_max: np.ndarray,
    ):
        self.hp_color_min = hp_color_min
        self.hp_color_max = hp_color_max
        self.mp_color_min = mp_color_min
        self.mp_color_max = mp_color_max

    def detect_bar_ratio(self, bar_image: np.ndarray, bar_type: str) -> float:
        """Detect the fill ratio of a bar image.

        Args:
            bar_image: BGR numpy array of the bar region
            bar_type: "hp" or "mp"

        Returns:
            Float between 0.0 and 1.0 representing the fill percentage.
        """
        if bar_image is None or bar_image.size == 0:
            return 0.0

        if bar_type == "hp":
            color_min = self.hp_color_min
            color_max = self.hp_color_max
        elif bar_type == "mp":
            color_min = self.mp_color_min
            color_max = self.mp_color_max
        else:
            log.error(f"Unknown bar type: {bar_type}")
            return 0.0

        mask = np.all((bar_image >= color_min) & (bar_image <= color_max), axis=2)
        total_pixels = mask.size
        colored_pixels = np.sum(mask)

        if total_pixels == 0:
            return 0.0

        ratio = colored_pixels / total_pixels
        return float(ratio)
