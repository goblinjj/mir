"""Game window finder and manager."""

import sys
from typing import Optional, Tuple

from src.utils.logger import log


class GameWindow:
    """Manages the game window handle and properties."""

    def __init__(self, window_title: str = "热血传奇"):
        self.window_title = window_title
        self.hwnd: Optional[int] = None

    def find_window(self) -> bool:
        """Find the game window by title. Returns True if found."""
        if sys.platform != "win32":
            log.warning("Window finding only works on Windows")
            return False

        import win32gui

        def callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title and "MirBot" not in title:
                    results.append(hwnd)

        results = []
        win32gui.EnumWindows(callback, results)

        if results:
            self.hwnd = results[0]
            title = win32gui.GetWindowText(self.hwnd)
            log.info(f"Found game window: hwnd={self.hwnd}, title='{title}'")
            return True

        log.warning(f"Game window not found: '{self.window_title}'")
        return False

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Get window position and size as (x, y, width, height)."""
        if self.hwnd is None:
            return None
        if sys.platform != "win32":
            return None

        import win32gui

        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        return (left, top, right - left, bottom - top)

    def get_client_size(self) -> Optional[Tuple[int, int]]:
        """Get client area size as (width, height)."""
        if self.hwnd is None:
            return None
        if sys.platform != "win32":
            return None

        import win32gui

        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        return (right - left, bottom - top)

    def is_valid(self) -> bool:
        """Check if the window handle is still valid."""
        if self.hwnd is None:
            return False
        if sys.platform != "win32":
            return False

        import win32gui

        return win32gui.IsWindow(self.hwnd)
