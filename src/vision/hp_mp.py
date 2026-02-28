"""HP and MP detection via OCR text reading."""

import re

import numpy as np

from src.utils.logger import log


def _init_ocr():
    """Initialize a lightweight OCR engine for reading HP/MP numbers."""
    try:
        import pytesseract
        # Quick smoke test
        pytesseract.get_tesseract_version()
        log.info("Using Tesseract OCR for HP/MP detection")
        return _TesseractOCR()
    except Exception:
        pass

    try:
        from paddleocr import PaddleOCR
        engine = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
        log.info("Using PaddleOCR for HP/MP detection")
        return _PaddleOCRWrapper(engine)
    except Exception:
        pass

    log.warning("No OCR engine available for HP/MP text detection")
    return None


class _TesseractOCR:
    """Tesseract OCR wrapper for reading numbers."""

    def read_text(self, image: np.ndarray) -> str:
        import pytesseract
        from PIL import Image

        gray = _preprocess_for_ocr(image)
        pil_img = Image.fromarray(gray)
        # digits + slash only
        text = pytesseract.image_to_string(
            pil_img,
            config="--psm 7 -c tessedit_char_whitelist=0123456789/",
        )
        return text.strip()


class _PaddleOCRWrapper:
    """PaddleOCR wrapper for reading numbers."""

    def __init__(self, engine):
        self.engine = engine

    def read_text(self, image: np.ndarray) -> str:
        gray = _preprocess_for_ocr(image)
        # PaddleOCR expects BGR 3-channel
        bgr = np.stack([gray, gray, gray], axis=2)
        results = self.engine.ocr(bgr, cls=False)
        if not results or not results[0]:
            return ""
        texts = [line[1][0] for line in results[0]]
        return " ".join(texts)


def _preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale and threshold to make white text readable."""
    if len(image.shape) == 3:
        # Convert to grayscale: use max channel to catch white/light text
        gray = np.max(image, axis=2)
    else:
        gray = image

    # Threshold: text pixels are bright (white/light colored)
    _, binary = gray.copy(), gray.copy()
    binary = np.where(gray > 150, 255, 0).astype(np.uint8)

    # Invert: OCR works better with dark text on white background
    binary = 255 - binary

    return binary


_RATIO_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")


def _parse_ratio(text: str) -> float:
    """Parse 'current/max' text into a ratio. Returns -1.0 on failure."""
    match = _RATIO_PATTERN.search(text)
    if not match:
        return -1.0
    current = int(match.group(1))
    maximum = int(match.group(2))
    if maximum <= 0:
        return -1.0
    return min(current / maximum, 1.0)


class HpMpDetector:
    """Detects HP/MP by OCR-reading the text values below the bars."""

    def __init__(self, **kwargs):
        # Accept and ignore legacy color kwargs for backward compatibility
        self.ocr = _init_ocr()
        self._last_hp_ratio = 1.0
        self._last_mp_ratio = 1.0

    def detect_ratio_from_text(self, text_image: np.ndarray) -> float:
        """Read a 'current/max' text region and return the ratio.

        Returns:
            Float between 0.0 and 1.0 on success, or -1.0 on failure.
        """
        if self.ocr is None:
            return -1.0
        if text_image is None or text_image.size == 0:
            return -1.0

        try:
            text = self.ocr.read_text(text_image)
            ratio = _parse_ratio(text)
            if ratio >= 0:
                log.debug(f"OCR read: '{text}' -> ratio={ratio:.2f}")
            return ratio
        except Exception as e:
            log.debug(f"OCR read failed: {e}")
            return -1.0

    def detect_hp_mp(
        self, frame: np.ndarray, hp_text_region: list, mp_text_region: list
    ) -> tuple:
        """Detect HP and MP ratios from text regions.

        Args:
            frame: Full game screenshot (BGR numpy array)
            hp_text_region: [x, y, w, h] of HP text area
            mp_text_region: [x, y, w, h] of MP text area

        Returns:
            (hp_ratio, mp_ratio) tuple, each 0.0-1.0
        """
        hp_img = self._crop(frame, hp_text_region)
        mp_img = self._crop(frame, mp_text_region)

        hp = self.detect_ratio_from_text(hp_img)
        mp = self.detect_ratio_from_text(mp_img)

        # Use last known good value if OCR fails this frame
        if hp >= 0:
            self._last_hp_ratio = hp
        if mp >= 0:
            self._last_mp_ratio = mp

        return self._last_hp_ratio, self._last_mp_ratio

    @staticmethod
    def _crop(frame: np.ndarray, region: list) -> np.ndarray:
        x, y, w, h = region
        return frame[y:y + h, x:x + w]

    # Legacy interface kept for backward compatibility with tests
    def detect_bar_ratio(self, bar_image: np.ndarray, bar_type: str) -> float:
        ratio = self.detect_ratio_from_text(bar_image)
        if ratio >= 0:
            return ratio
        return 0.0
