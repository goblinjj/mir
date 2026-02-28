"""Screen capture module for game window."""

import sys
from typing import Optional, List

import numpy as np

from src.utils.logger import log


class ScreenCapture:
    """Captures screenshots from the game window."""

    def __init__(self):
        self.last_frame: Optional[np.ndarray] = None

    def capture(self, hwnd: int) -> Optional[np.ndarray]:
        """Capture a screenshot of the given window. Returns BGR numpy array."""
        if sys.platform != "win32":
            log.warning("Screen capture only works on Windows")
            return None

        import win32gui
        import win32ui
        import win32con
        from PIL import Image

        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                return None

            hwnd_dc = win32gui.GetDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

            bmp_info = bitmap.GetInfo()
            bmp_data = bitmap.GetBitmapBits(True)

            img = Image.frombuffer("RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]), bmp_data, "raw", "BGRX", 0, 1)

            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            frame = np.array(img)
            self.last_frame = frame
            return frame

        except Exception as e:
            log.error(f"Screen capture failed: {e}")
            return None

    def crop_region(self, frame: np.ndarray, region: List[int]) -> np.ndarray:
        """Crop a region from the frame. region = [x, y, width, height]."""
        x, y, w, h = region
        return frame[y:y + h, x:x + w]
