"""Keyboard input simulation for game window."""

import sys
import time
from typing import Optional

from src.utils.logger import log

VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "ESC": 0x1B, "ENTER": 0x0D, "SPACE": 0x20, "TAB": 0x09,
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
}


class KeyboardSim:
    """Simulates keyboard input to a window."""

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd

    def press_key(self, key: str, hold_time: float = 0.05):
        """Press and release a key."""
        if sys.platform != "win32":
            log.debug(f"[Stub] press_key: {key}")
            return

        import win32api
        import win32con
        import win32gui

        vk = VK_MAP.get(key.upper())
        if vk is None:
            log.error(f"Unknown key: {key}")
            return

        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, 0)
            time.sleep(hold_time)
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, 0)
        else:
            win32api.keybd_event(vk, 0, 0, 0)
            time.sleep(hold_time)
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
