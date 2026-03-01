"""Mouse input simulation for game window."""

import sys
import time
from typing import Optional

from src.utils.logger import log


class MouseSim:
    """Simulates mouse input to a window."""

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd

    def click(self, x: int, y: int, button: str = "left"):
        """Click at position (x, y) relative to the window."""
        if sys.platform != "win32":
            log.debug(f"[Stub] click: ({x}, {y}) {button}")
            return

        import win32api
        import win32con
        import win32gui

        lparam = (y << 16) | (x & 0xFFFF)

        if button == "left":
            down_msg = win32con.WM_LBUTTONDOWN
            up_msg = win32con.WM_LBUTTONUP
            wparam = win32con.MK_LBUTTON
        else:
            down_msg = win32con.WM_RBUTTONDOWN
            up_msg = win32con.WM_RBUTTONUP
            wparam = win32con.MK_RBUTTON

        if self.hwnd:
            win32gui.PostMessage(self.hwnd, down_msg, wparam, lparam)
            time.sleep(0.05)
            win32gui.PostMessage(self.hwnd, up_msg, 0, lparam)
        else:
            win32api.SetCursorPos((x, y))
            time.sleep(0.02)
            if button == "left":
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def move(self, x: int, y: int):
        """Move the mouse to position (x, y) relative to window."""
        if sys.platform != "win32":
            log.debug(f"[Stub] move: ({x}, {y})")
            return

        import win32con
        import win32gui

        lparam = (y << 16) | (x & 0xFFFF)
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
