# MirBot 法师自动练级 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python-based auto-leveling bot for Mage class in Legend of Mir (996 engine private server), using screen capture + OCR + simulated input.

**Architecture:** Modular pipeline — screen capture feeds into vision engine (OCR + color analysis), which updates game state, which feeds a finite state machine strategy layer, which emits actions executed via simulated keyboard/mouse. GUI provides control and monitoring.

**Tech Stack:** Python 3.11+, OpenCV, PaddleOCR, PyQt5, win32gui/win32api (Windows), PyYAML, pytest

**NOTE:** This project targets Windows. Modules using `win32gui`/`win32api` can only be fully tested on Windows. Platform-independent logic (state management, strategy, config) can be developed and unit-tested on any OS.

---

### Task 1: Project Scaffold & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `main.py`
- Create: `config.yaml`
- Create: `src/__init__.py`
- Create: `src/capture/__init__.py`
- Create: `src/vision/__init__.py`
- Create: `src/state/__init__.py`
- Create: `src/strategy/__init__.py`
- Create: `src/action/__init__.py`
- Create: `src/gui/__init__.py`
- Create: `src/utils/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: Initialize git repo**

```bash
cd /Volumes/T7/work/mir
git init
```

**Step 2: Create .gitignore**

```gitignore
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.idea/
.vscode/
*.log
src/vision/templates/*.png
```

**Step 3: Create requirements.txt**

```txt
opencv-python>=4.8.0
paddleocr>=2.7.0
paddlepaddle>=2.5.0
PyQt5>=5.15.0
PyYAML>=6.0
Pillow>=10.0.0
pywin32>=306; sys_platform == "win32"
numpy>=1.24.0
pytest>=7.4.0
```

**Step 4: Create config.yaml with default settings**

```yaml
# MirBot 配置文件
game:
  window_title: "热血传奇"  # 游戏窗口标题（用于查找窗口）

player:
  hp_threshold: 0.5       # HP 低于此比例吃红药
  mp_threshold: 0.3       # MP 低于此比例吃蓝药
  potion_min_count: 5     # 药品低于此数量回城补给

skills:
  attack_single: "F1"     # 单体攻击（雷电术）
  attack_aoe: "F2"        # AOE 攻击（地狱火/火墙）
  shield: "F3"            # 防御技能（抗拒火环）
  summon: "F4"            # 召唤技能（召唤神兽）
  boss_skill: "F5"        # Boss 技能（冰咆哮）

leveling:
  mode: "fire"            # 练级模式: "fire" 或 "pet"
  patrol_points: []       # 巡逻路径点 [[x,y], [x,y], ...]
  loot_enabled: true      # 是否捡物品
  loot_filter: []         # 物品过滤（空=全捡）

pet:
  pull_count: 3           # 引怪数量目标
  safe_distance: 200      # 安全距离（像素）

screen:
  hp_bar_region: [10, 40, 160, 52]   # 血条区域 [x, y, w, h]
  mp_bar_region: [10, 56, 160, 68]   # 蓝条区域 [x, y, w, h]
  game_area: [0, 0, 800, 600]        # 游戏画面区域

colors:
  hp_red: [180, 0, 0]      # 血条红色 RGB 范围下限
  hp_red_max: [255, 80, 80] # 血条红色 RGB 范围上限
  mp_blue: [0, 0, 180]     # 蓝条蓝色 RGB 范围下限
  mp_blue_max: [80, 80, 255] # 蓝条蓝色 RGB 范围上限
```

**Step 5: Create main.py stub**

```python
"""MirBot - 热血传奇法师自动练级工具"""

import sys


def main():
    print("MirBot starting...")
    # TODO: Launch GUI
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 6: Create all __init__.py files and directory structure**

```bash
mkdir -p src/capture src/vision/templates src/state src/strategy src/action src/gui src/utils tests
touch src/__init__.py src/capture/__init__.py src/vision/__init__.py src/state/__init__.py
touch src/strategy/__init__.py src/action/__init__.py src/gui/__init__.py src/utils/__init__.py
touch tests/__init__.py
```

**Step 7: Commit**

```bash
git add .
git commit -m "feat: project scaffold with dependencies and config"
```

---

### Task 2: Config Loader

**Files:**
- Create: `src/utils/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import tempfile

import yaml
import pytest

from src.utils.config import load_config, Config


def test_load_config_from_file():
    data = {
        "game": {"window_title": "测试传奇"},
        "player": {"hp_threshold": 0.6, "mp_threshold": 0.4, "potion_min_count": 10},
        "skills": {"attack_single": "F1", "attack_aoe": "F2", "shield": "F3", "summon": "F4", "boss_skill": "F5"},
        "leveling": {"mode": "fire", "patrol_points": [], "loot_enabled": True, "loot_filter": []},
        "pet": {"pull_count": 3, "safe_distance": 200},
        "screen": {
            "hp_bar_region": [10, 40, 160, 52],
            "mp_bar_region": [10, 56, 160, 68],
            "game_area": [0, 0, 800, 600],
        },
        "colors": {
            "hp_red": [180, 0, 0], "hp_red_max": [255, 80, 80],
            "mp_blue": [0, 0, 180], "mp_blue_max": [80, 80, 255],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        path = f.name
    try:
        config = load_config(path)
        assert isinstance(config, Config)
        assert config.game.window_title == "测试传奇"
        assert config.player.hp_threshold == 0.6
        assert config.leveling.mode == "fire"
    finally:
        os.unlink(path)


def test_load_default_config():
    config = load_config("config.yaml")
    assert config.player.hp_threshold == 0.5
    assert config.player.mp_threshold == 0.3
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.utils.config'`

**Step 3: Write implementation**

```python
# src/utils/config.py
"""Configuration loader for MirBot."""

from dataclasses import dataclass, field
from typing import List, Tuple

import yaml


@dataclass
class GameConfig:
    window_title: str = "热血传奇"


@dataclass
class PlayerConfig:
    hp_threshold: float = 0.5
    mp_threshold: float = 0.3
    potion_min_count: int = 5


@dataclass
class SkillsConfig:
    attack_single: str = "F1"
    attack_aoe: str = "F2"
    shield: str = "F3"
    summon: str = "F4"
    boss_skill: str = "F5"


@dataclass
class LevelingConfig:
    mode: str = "fire"
    patrol_points: List[List[int]] = field(default_factory=list)
    loot_enabled: bool = True
    loot_filter: List[str] = field(default_factory=list)


@dataclass
class PetConfig:
    pull_count: int = 3
    safe_distance: int = 200


@dataclass
class ScreenConfig:
    hp_bar_region: List[int] = field(default_factory=lambda: [10, 40, 160, 52])
    mp_bar_region: List[int] = field(default_factory=lambda: [10, 56, 160, 68])
    game_area: List[int] = field(default_factory=lambda: [0, 0, 800, 600])


@dataclass
class ColorsConfig:
    hp_red: List[int] = field(default_factory=lambda: [180, 0, 0])
    hp_red_max: List[int] = field(default_factory=lambda: [255, 80, 80])
    mp_blue: List[int] = field(default_factory=lambda: [0, 0, 180])
    mp_blue_max: List[int] = field(default_factory=lambda: [80, 80, 255])


@dataclass
class Config:
    game: GameConfig = field(default_factory=GameConfig)
    player: PlayerConfig = field(default_factory=PlayerConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    leveling: LevelingConfig = field(default_factory=LevelingConfig)
    pet: PetConfig = field(default_factory=PetConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    colors: ColorsConfig = field(default_factory=ColorsConfig)


def _dict_to_dataclass(cls, data: dict):
    """Convert a dict to a dataclass, ignoring unknown keys."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def load_config(path: str) -> Config:
    """Load config from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Config(
        game=_dict_to_dataclass(GameConfig, raw.get("game", {})),
        player=_dict_to_dataclass(PlayerConfig, raw.get("player", {})),
        skills=_dict_to_dataclass(SkillsConfig, raw.get("skills", {})),
        leveling=_dict_to_dataclass(LevelingConfig, raw.get("leveling", {})),
        pet=_dict_to_dataclass(PetConfig, raw.get("pet", {})),
        screen=_dict_to_dataclass(ScreenConfig, raw.get("screen", {})),
        colors=_dict_to_dataclass(ColorsConfig, raw.get("colors", {})),
    )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/utils/config.py tests/test_config.py
git commit -m "feat: config loader with YAML support and dataclass mapping"
```

---

### Task 3: Logger Utility

**Files:**
- Create: `src/utils/logger.py`

**Step 1: Write logger module**

```python
# src/utils/logger.py
"""Logging setup for MirBot."""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "mirbot", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Create and configure a logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


log = setup_logger()
```

**Step 2: Commit**

```bash
git add src/utils/logger.py
git commit -m "feat: logger utility with console and file output"
```

---

### Task 4: Game Window Manager

**Files:**
- Create: `src/capture/window.py`
- Create: `tests/test_window.py`

**Step 1: Write the failing test**

```python
# tests/test_window.py
"""Tests for window manager (platform-independent logic only)."""

import pytest

from src.capture.window import GameWindow


def test_game_window_init():
    gw = GameWindow(window_title="测试窗口")
    assert gw.window_title == "测试窗口"
    assert gw.hwnd is None


def test_game_window_not_found():
    gw = GameWindow(window_title="不存在的窗口_XYZ_12345")
    found = gw.find_window()
    assert found is False
    assert gw.hwnd is None
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_window.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/capture/window.py
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
                if self.window_title in title:
                    results.append(hwnd)

        results = []
        win32gui.EnumWindows(callback, results)

        if results:
            self.hwnd = results[0]
            log.info(f"Found game window: hwnd={self.hwnd}")
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

    def is_valid(self) -> bool:
        """Check if the window handle is still valid."""
        if self.hwnd is None:
            return False
        if sys.platform != "win32":
            return False

        import win32gui

        return win32gui.IsWindow(self.hwnd)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_window.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/capture/window.py tests/test_window.py
git commit -m "feat: game window manager with find and rect support"
```

---

### Task 5: Screen Capture Module

**Files:**
- Create: `src/capture/screen.py`
- Create: `tests/test_screen.py`

**Step 1: Write the failing test**

```python
# tests/test_screen.py
"""Tests for screen capture (platform-independent logic)."""

import numpy as np
import pytest

from src.capture.screen import ScreenCapture


def test_screen_capture_init():
    sc = ScreenCapture()
    assert sc.last_frame is None


def test_crop_region():
    sc = ScreenCapture()
    # Simulate a 600x800 RGB image
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    frame[40:52, 10:170] = [255, 0, 0]  # Red bar region

    cropped = sc.crop_region(frame, [10, 40, 160, 12])
    assert cropped.shape == (12, 160, 3)
    assert np.all(cropped[0, 0] == [255, 0, 0])
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_screen.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/capture/screen.py
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

            # PrintWindow for background capture
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

            bmp_info = bitmap.GetInfo()
            bmp_data = bitmap.GetBitmapBits(True)

            img = Image.frombuffer("RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]), bmp_data, "raw", "BGRX", 0, 1)

            # Cleanup
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
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_screen.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/capture/screen.py tests/test_screen.py
git commit -m "feat: screen capture with background window support and crop"
```

---

### Task 6: HP/MP Bar Recognition

**Files:**
- Create: `src/vision/hp_mp.py`
- Create: `tests/test_hp_mp.py`

**Step 1: Write the failing test**

```python
# tests/test_hp_mp.py
"""Tests for HP/MP bar recognition."""

import numpy as np
import pytest

from src.vision.hp_mp import HpMpDetector


@pytest.fixture
def detector():
    return HpMpDetector(
        hp_color_min=np.array([0, 0, 180]),
        hp_color_max=np.array([80, 80, 255]),
        mp_color_min=np.array([180, 0, 0]),
        mp_color_max=np.array([255, 80, 80]),
    )


def test_full_hp_bar(detector):
    # Create a fully red bar (in RGB: R=200, G=10, B=10 -> in BGR for OpenCV: B=10, G=10, R=200)
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [10, 10, 200]  # BGR: full red
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert ratio > 0.9


def test_half_hp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :80] = [10, 10, 200]  # Left half red
    bar[:, 80:] = [30, 30, 30]   # Right half dark
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert 0.4 < ratio < 0.6


def test_empty_hp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [30, 30, 30]  # All dark
    ratio = detector.detect_bar_ratio(bar, "hp")
    assert ratio < 0.1


def test_full_mp_bar(detector):
    bar = np.zeros((12, 160, 3), dtype=np.uint8)
    bar[:, :] = [200, 10, 10]  # BGR: full blue
    ratio = detector.detect_bar_ratio(bar, "mp")
    assert ratio > 0.9
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hp_mp.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/vision/hp_mp.py
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
        # Colors are in BGR format (OpenCV convention)
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

        # Create mask for pixels within color range
        mask = np.all((bar_image >= color_min) & (bar_image <= color_max), axis=2)
        total_pixels = mask.size
        colored_pixels = np.sum(mask)

        if total_pixels == 0:
            return 0.0

        ratio = colored_pixels / total_pixels
        return float(ratio)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_hp_mp.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/vision/hp_mp.py tests/test_hp_mp.py
git commit -m "feat: HP/MP bar detection via color ratio analysis"
```

---

### Task 7: OCR Monster Detection

**Files:**
- Create: `src/vision/ocr.py`
- Create: `tests/test_ocr.py`

**Step 1: Write the failing test**

```python
# tests/test_ocr.py
"""Tests for OCR monster detection."""

import pytest

from src.vision.ocr import MonsterDetector, DetectedMonster


def test_detected_monster_dataclass():
    m = DetectedMonster(name="鸡", x=400, y=300, confidence=0.95)
    assert m.name == "鸡"
    assert m.x == 400
    assert m.y == 300
    assert m.confidence == 0.95


def test_monster_detector_init():
    md = MonsterDetector()
    assert md.ocr_engine is not None


def test_classify_monster_type():
    md = MonsterDetector()
    assert md.classify("鸡") == "normal"
    assert md.classify("祖玛教主") == "boss"
    # Custom boss list
    md2 = MonsterDetector(boss_names=["测试Boss"])
    assert md2.classify("测试Boss") == "boss"
    assert md2.classify("小鸡") == "normal"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/vision/ocr.py
"""OCR-based monster detection."""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from src.utils.logger import log

# Default boss names for Legend of Mir
DEFAULT_BOSS_NAMES = [
    "祖玛教主", "沃玛教主", "虹魔教主", "白野猪", "黑锷蜘蛛",
    "赤月恶魔", "触龙神", "骷髅精灵", "双头血魔", "牛魔王",
    "火龙神", "冰眼", "邪恶钳虫", "幻境迷宫",
]


@dataclass
class DetectedMonster:
    """A monster detected on screen."""
    name: str
    x: int           # Center X position on screen
    y: int           # Center Y position on screen (estimated body position, below name)
    confidence: float


class MonsterDetector:
    """Detects monsters by OCR-reading their overhead names."""

    def __init__(self, boss_names: Optional[List[str]] = None):
        self.boss_names = boss_names or DEFAULT_BOSS_NAMES
        self.ocr_engine = self._init_ocr()

    def _init_ocr(self):
        """Initialize PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR
            return PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
        except ImportError:
            log.warning("PaddleOCR not installed, using stub")
            return _StubOCR()

    def detect(self, frame: np.ndarray) -> List[DetectedMonster]:
        """Detect all monsters in the given frame.

        Args:
            frame: BGR numpy array of the game screen.

        Returns:
            List of detected monsters with positions.
        """
        if frame is None or frame.size == 0:
            return []

        results = self.ocr_engine.ocr(frame, cls=False)
        monsters = []

        if not results or not results[0]:
            return []

        for line in results[0]:
            bbox, (text, confidence) = line
            if confidence < 0.5:
                continue

            # Calculate center position of the text
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            cx = int(sum(xs) / len(xs))
            cy = int(sum(ys) / len(ys))

            # Monster body is below the name text
            body_y = cy + 30

            monsters.append(DetectedMonster(
                name=text.strip(),
                x=cx,
                y=body_y,
                confidence=confidence,
            ))

        return monsters

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
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_ocr.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/vision/ocr.py tests/test_ocr.py
git commit -m "feat: OCR monster detection with PaddleOCR and classification"
```

---

### Task 8: Player State Model

**Files:**
- Create: `src/state/player.py`
- Create: `src/state/game.py`
- Create: `tests/test_state.py`

**Step 1: Write the failing test**

```python
# tests/test_state.py
"""Tests for game state management."""

import pytest

from src.state.player import PlayerState
from src.state.game import GameState


def test_player_state_init():
    ps = PlayerState()
    assert ps.hp_ratio == 1.0
    assert ps.mp_ratio == 1.0
    assert ps.is_dead is False


def test_player_needs_hp_potion():
    ps = PlayerState()
    ps.hp_ratio = 0.3
    assert ps.needs_hp_potion(threshold=0.5) is True
    ps.hp_ratio = 0.7
    assert ps.needs_hp_potion(threshold=0.5) is False


def test_player_needs_mp_potion():
    ps = PlayerState()
    ps.mp_ratio = 0.2
    assert ps.needs_mp_potion(threshold=0.3) is True


def test_player_is_dead():
    ps = PlayerState()
    ps.hp_ratio = 0.0
    assert ps.is_dead is True


def test_game_state_init():
    gs = GameState()
    assert gs.player is not None
    assert gs.monsters == []
    assert gs.current_map == ""


def test_game_state_has_monsters():
    gs = GameState()
    assert gs.has_monsters() is False
    gs.monsters = [{"name": "鸡", "x": 100, "y": 200}]
    assert gs.has_monsters() is True


def test_game_state_nearest_monster():
    gs = GameState()
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.monsters = [
        {"name": "鸡", "x": 500, "y": 300},
        {"name": "鹿", "x": 410, "y": 310},
    ]
    nearest = gs.nearest_monster()
    assert nearest["name"] == "鹿"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/state/player.py
"""Player state tracking."""

from dataclasses import dataclass


@dataclass
class PlayerState:
    """Tracks the player's current state."""
    hp_ratio: float = 1.0       # 0.0 to 1.0
    mp_ratio: float = 1.0       # 0.0 to 1.0
    screen_x: int = 0           # Player position on screen
    screen_y: int = 0
    level: int = 0
    has_pet: bool = False

    @property
    def is_dead(self) -> bool:
        return self.hp_ratio <= 0.0

    def needs_hp_potion(self, threshold: float) -> bool:
        return self.hp_ratio < threshold

    def needs_mp_potion(self, threshold: float) -> bool:
        return self.mp_ratio < threshold
```

```python
# src/state/game.py
"""Game state aggregation."""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from src.state.player import PlayerState


@dataclass
class GameState:
    """Aggregated game state."""
    player: PlayerState = field(default_factory=PlayerState)
    monsters: List[Dict] = field(default_factory=list)
    current_map: str = ""
    pet_alive: bool = False

    def has_monsters(self) -> bool:
        return len(self.monsters) > 0

    def nearest_monster(self) -> Optional[Dict]:
        """Find the nearest monster to the player."""
        if not self.monsters:
            return None

        px, py = self.player.screen_x, self.player.screen_y

        def distance(m):
            return math.hypot(m["x"] - px, m["y"] - py)

        return min(self.monsters, key=distance)

    def monster_count(self) -> int:
        return len(self.monsters)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_state.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add src/state/player.py src/state/game.py tests/test_state.py
git commit -m "feat: player and game state models"
```

---

### Task 9: Keyboard & Mouse Input Simulation

**Files:**
- Create: `src/action/keyboard.py`
- Create: `src/action/mouse.py`
- Create: `src/action/skills.py`
- Create: `tests/test_action.py`

**Step 1: Write the failing test**

```python
# tests/test_action.py
"""Tests for action modules (platform-independent logic)."""

import pytest

from src.action.skills import SkillManager


def test_skill_manager_init():
    keys = {
        "attack_single": "F1",
        "attack_aoe": "F2",
        "shield": "F3",
        "summon": "F4",
        "boss_skill": "F5",
    }
    sm = SkillManager(keys)
    assert sm.get_key("attack_single") == "F1"
    assert sm.get_key("shield") == "F3"


def test_skill_manager_unknown_skill():
    sm = SkillManager({"attack_single": "F1"})
    assert sm.get_key("nonexistent") is None


def test_skill_cooldown():
    sm = SkillManager({"attack_single": "F1"})
    assert sm.is_ready("attack_single") is True
    sm.use_skill("attack_single", cooldown=1.0)
    assert sm.is_ready("attack_single") is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/action/keyboard.py
"""Keyboard input simulation for game window."""

import sys
import time
from typing import Optional

from src.utils.logger import log

# Virtual key code mapping
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
```

```python
# src/action/mouse.py
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
        else:
            down_msg = win32con.WM_RBUTTONDOWN
            up_msg = win32con.WM_RBUTTONUP

        if self.hwnd:
            win32gui.PostMessage(self.hwnd, down_msg, 0, lparam)
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
```

```python
# src/action/skills.py
"""Skill management with cooldown tracking."""

import time
from typing import Dict, Optional


class SkillManager:
    """Manages skill key mappings and cooldowns."""

    def __init__(self, key_mapping: Dict[str, str]):
        self._keys = key_mapping
        self._last_used: Dict[str, float] = {}
        self._cooldowns: Dict[str, float] = {}

    def get_key(self, skill_name: str) -> Optional[str]:
        """Get the key binding for a skill."""
        return self._keys.get(skill_name)

    def use_skill(self, skill_name: str, cooldown: float = 0.0):
        """Record that a skill was used, setting its cooldown."""
        self._last_used[skill_name] = time.time()
        self._cooldowns[skill_name] = cooldown

    def is_ready(self, skill_name: str) -> bool:
        """Check if a skill is off cooldown."""
        if skill_name not in self._last_used:
            return True
        elapsed = time.time() - self._last_used[skill_name]
        cd = self._cooldowns.get(skill_name, 0.0)
        return elapsed >= cd
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_action.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/action/keyboard.py src/action/mouse.py src/action/skills.py tests/test_action.py
git commit -m "feat: keyboard/mouse simulation and skill manager with cooldowns"
```

---

### Task 10: Strategy Base — State Machine

**Files:**
- Create: `src/strategy/base.py`
- Create: `tests/test_strategy_base.py`

**Step 1: Write the failing test**

```python
# tests/test_strategy_base.py
"""Tests for strategy state machine base."""

import pytest

from src.strategy.base import StateMachine, State


class IdleState(State):
    name = "idle"

    def enter(self, ctx):
        ctx["entered_idle"] = True

    def execute(self, ctx):
        if ctx.get("start_fight"):
            return "fight"
        return None

    def exit(self, ctx):
        ctx["exited_idle"] = True


class FightState(State):
    name = "fight"

    def execute(self, ctx):
        ctx["fighting"] = True
        return "idle"


def test_state_machine_transitions():
    sm = StateMachine()
    sm.add_state(IdleState())
    sm.add_state(FightState())
    sm.set_initial("idle")

    ctx = {}
    sm.update(ctx)  # idle.execute -> stays idle
    assert ctx.get("entered_idle") is True

    ctx["start_fight"] = True
    sm.update(ctx)  # idle.execute -> returns "fight"
    assert ctx.get("exited_idle") is True
    assert sm.current_state.name == "fight"

    sm.update(ctx)  # fight.execute -> returns "idle"
    assert ctx.get("fighting") is True
    assert sm.current_state.name == "idle"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_strategy_base.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/strategy/base.py
"""State machine base for bot strategy."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from src.utils.logger import log


class State(ABC):
    """Base class for a state in the state machine."""

    name: str = "unnamed"

    def enter(self, ctx: dict):
        """Called when entering this state."""
        pass

    @abstractmethod
    def execute(self, ctx: dict) -> Optional[str]:
        """Execute state logic. Return next state name to transition, or None to stay."""
        pass

    def exit(self, ctx: dict):
        """Called when leaving this state."""
        pass


class StateMachine:
    """Simple finite state machine."""

    def __init__(self):
        self._states: Dict[str, State] = {}
        self.current_state: Optional[State] = None

    def add_state(self, state: State):
        """Register a state."""
        self._states[state.name] = state

    def set_initial(self, state_name: str):
        """Set the initial state."""
        self.current_state = self._states[state_name]
        self.current_state.enter({})

    def update(self, ctx: dict):
        """Run one tick of the state machine."""
        if self.current_state is None:
            return

        next_name = self.current_state.execute(ctx)

        if next_name and next_name != self.current_state.name:
            if next_name not in self._states:
                log.error(f"Unknown state: {next_name}")
                return
            self.current_state.exit(ctx)
            self.current_state = self._states[next_name]
            self.current_state.enter(ctx)
            log.info(f"State -> {next_name}")
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_strategy_base.py -v`
Expected: 1 passed

**Step 5: Commit**

```bash
git add src/strategy/base.py tests/test_strategy_base.py
git commit -m "feat: state machine base for bot strategy"
```

---

### Task 11: Fire Mage Strategy

**Files:**
- Create: `src/strategy/fire_mage.py`
- Create: `tests/test_fire_mage.py`

**Step 1: Write the failing test**

```python
# tests/test_fire_mage.py
"""Tests for fire mage leveling strategy."""

import pytest

from src.strategy.fire_mage import build_fire_mage_fsm
from src.state.game import GameState
from src.state.player import PlayerState


def make_ctx(hp=1.0, mp=1.0, monsters=None, hp_threshold=0.5, mp_threshold=0.3):
    gs = GameState()
    gs.player.hp_ratio = hp
    gs.player.mp_ratio = mp
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.monsters = monsters or []
    return {
        "game_state": gs,
        "hp_threshold": hp_threshold,
        "mp_threshold": mp_threshold,
        "actions": [],
    }


def test_patrol_to_combat_on_monster():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.update(ctx)  # patrol -> sees monster -> transition to combat
    assert sm.current_state.name == "combat"


def test_patrol_stays_when_no_monster():
    sm = build_fire_mage_fsm()
    ctx = make_ctx()
    sm.update(ctx)
    assert sm.current_state.name == "patrol"


def test_combat_to_heal_when_low_hp():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.3, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("combat")
    sm.update(ctx)
    assert sm.current_state.name == "heal"


def test_combat_to_loot_when_no_monsters():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.8, monsters=[])
    sm.set_initial("combat")
    sm.update(ctx)
    assert sm.current_state.name == "loot"


def test_heal_to_combat_when_hp_ok():
    sm = build_fire_mage_fsm()
    ctx = make_ctx(hp=0.8, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("heal")
    sm.update(ctx)
    # After healing, should go back to patrol or combat
    assert sm.current_state.name in ("patrol", "combat")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fire_mage.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/strategy/fire_mage.py
"""Fire mage leveling strategy — state machine states."""

from typing import Optional

from src.strategy.base import State, StateMachine
from src.utils.logger import log


class PatrolState(State):
    name = "patrol"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.has_monsters():
            return "combat"
        # Queue patrol movement action
        ctx["actions"].append({"type": "patrol_move"})
        return None


class CombatState(State):
    name = "combat"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]

        if gs.player.is_dead:
            return "dead"

        # Check if healing needed
        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"

        # No monsters left -> loot
        if not gs.has_monsters():
            return "loot"

        # Check MP for potions
        if gs.player.needs_mp_potion(ctx["mp_threshold"]):
            ctx["actions"].append({"type": "use_mp_potion"})

        # Choose skill based on monster count
        target = gs.nearest_monster()
        if gs.monster_count() >= 3:
            ctx["actions"].append({"type": "use_skill", "skill": "attack_aoe", "target": target})
        else:
            ctx["actions"].append({"type": "use_skill", "skill": "attack_single", "target": target})

        return None


class HealState(State):
    name = "heal"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]

        # Use shield if monsters nearby
        if gs.has_monsters():
            ctx["actions"].append({"type": "use_skill", "skill": "shield"})

        ctx["actions"].append({"type": "use_hp_potion"})

        # If HP is OK, return to patrol
        if not gs.player.needs_hp_potion(ctx["hp_threshold"]):
            if gs.has_monsters():
                return "combat"
            return "patrol"

        return None


class LootState(State):
    name = "loot"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        # Queue loot pickup action
        ctx["actions"].append({"type": "loot_pickup"})
        return "patrol"


class DeadState(State):
    name = "dead"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if not gs.player.is_dead:
            return "patrol"
        ctx["actions"].append({"type": "revive"})
        return None


class ResupplyState(State):
    name = "resupply"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "go_town_buy"})
        return "patrol"


def build_fire_mage_fsm() -> StateMachine:
    """Build and return the fire mage strategy state machine."""
    sm = StateMachine()
    sm.add_state(PatrolState())
    sm.add_state(CombatState())
    sm.add_state(HealState())
    sm.add_state(LootState())
    sm.add_state(DeadState())
    sm.add_state(ResupplyState())
    sm.set_initial("patrol")
    return sm
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_fire_mage.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/strategy/fire_mage.py tests/test_fire_mage.py
git commit -m "feat: fire mage leveling strategy with patrol/combat/heal/loot states"
```

---

### Task 12: Pet Mage Strategy

**Files:**
- Create: `src/strategy/pet_mage.py`
- Create: `tests/test_pet_mage.py`

**Step 1: Write the failing test**

```python
# tests/test_pet_mage.py
"""Tests for pet mage leveling strategy."""

import pytest

from src.strategy.pet_mage import build_pet_mage_fsm
from src.state.game import GameState


def make_ctx(hp=1.0, mp=1.0, monsters=None, pet_alive=False, hp_threshold=0.5, mp_threshold=0.3):
    gs = GameState()
    gs.player.hp_ratio = hp
    gs.player.mp_ratio = mp
    gs.player.screen_x = 400
    gs.player.screen_y = 300
    gs.player.has_pet = pet_alive
    gs.pet_alive = pet_alive
    gs.monsters = monsters or []
    return {
        "game_state": gs,
        "hp_threshold": hp_threshold,
        "mp_threshold": mp_threshold,
        "actions": [],
    }


def test_check_pet_summons_when_no_pet():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=False)
    sm.update(ctx)  # check_pet -> summon
    assert sm.current_state.name == "summon_pet"


def test_check_pet_to_pull_when_pet_alive():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True)
    sm.update(ctx)
    assert sm.current_state.name == "pull"


def test_pull_to_evade_when_monsters_found():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("pull")
    sm.update(ctx)
    assert sm.current_state.name == "evade"


def test_evade_to_loot_when_monsters_dead():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(pet_alive=True, monsters=[])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "loot"


def test_evade_heal_when_low_hp():
    sm = build_pet_mage_fsm()
    ctx = make_ctx(hp=0.3, pet_alive=True, monsters=[{"name": "鸡", "x": 450, "y": 320, "type": "normal"}])
    sm.set_initial("evade")
    sm.update(ctx)
    assert sm.current_state.name == "heal"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pet_mage.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/strategy/pet_mage.py
"""Pet mage leveling strategy — summon pet, pull mobs, evade."""

from typing import Optional

from src.strategy.base import State, StateMachine
from src.utils.logger import log


class CheckPetState(State):
    name = "check_pet"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if gs.pet_alive:
            return "pull"
        return "summon_pet"


class SummonPetState(State):
    name = "summon_pet"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "use_skill", "skill": "summon"})
        ctx["game_state"].pet_alive = True
        return "pull"


class PullState(State):
    name = "pull"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"

        if gs.has_monsters():
            # Monsters found, run towards them then back to pet
            ctx["actions"].append({"type": "pull_monsters"})
            return "evade"

        # No monsters, patrol to find some
        ctx["actions"].append({"type": "patrol_move"})
        return None


class EvadeState(State):
    name = "evade"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if gs.player.is_dead:
            return "dead"

        if gs.player.needs_hp_potion(ctx["hp_threshold"]):
            return "heal"

        if not gs.pet_alive:
            return "check_pet"

        if not gs.has_monsters():
            return "loot"

        # Keep evading — move away from monsters
        ctx["actions"].append({"type": "evade_monsters"})

        if gs.player.needs_mp_potion(ctx["mp_threshold"]):
            ctx["actions"].append({"type": "use_mp_potion"})

        return None


class PetHealState(State):
    name = "heal"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]

        if gs.has_monsters():
            ctx["actions"].append({"type": "use_skill", "skill": "shield"})

        ctx["actions"].append({"type": "use_hp_potion"})

        if not gs.player.needs_hp_potion(ctx["hp_threshold"]):
            if gs.has_monsters():
                return "evade"
            return "pull"

        return None


class PetLootState(State):
    name = "loot"

    def execute(self, ctx: dict) -> Optional[str]:
        ctx["actions"].append({"type": "loot_pickup"})
        return "pull"


class PetDeadState(State):
    name = "dead"

    def execute(self, ctx: dict) -> Optional[str]:
        gs = ctx["game_state"]
        if not gs.player.is_dead:
            return "check_pet"
        ctx["actions"].append({"type": "revive"})
        return None


def build_pet_mage_fsm() -> StateMachine:
    """Build and return the pet mage strategy state machine."""
    sm = StateMachine()
    sm.add_state(CheckPetState())
    sm.add_state(SummonPetState())
    sm.add_state(PullState())
    sm.add_state(EvadeState())
    sm.add_state(PetHealState())
    sm.add_state(PetLootState())
    sm.add_state(PetDeadState())
    sm.set_initial("check_pet")
    return sm
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_pet_mage.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/strategy/pet_mage.py tests/test_pet_mage.py
git commit -m "feat: pet mage leveling strategy with pull/evade/summon states"
```

---

### Task 13: Action Executor — Connects Strategy to Input

**Files:**
- Create: `src/action/executor.py`
- Create: `tests/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/test_executor.py
"""Tests for action executor."""

import pytest

from src.action.executor import ActionExecutor


class FakeKeyboard:
    def __init__(self):
        self.pressed = []
    def press_key(self, key, hold_time=0.05):
        self.pressed.append(key)


class FakeMouse:
    def __init__(self):
        self.clicks = []
    def click(self, x, y, button="left"):
        self.clicks.append((x, y, button))


def test_executor_use_skill():
    kb = FakeKeyboard()
    ms = FakeMouse()
    skill_keys = {"attack_single": "F1", "attack_aoe": "F2", "shield": "F3", "summon": "F4"}
    ex = ActionExecutor(kb, ms, skill_keys)

    ex.execute({"type": "use_skill", "skill": "attack_single", "target": {"x": 500, "y": 300}})
    assert "F1" in kb.pressed


def test_executor_use_hp_potion():
    kb = FakeKeyboard()
    ms = FakeMouse()
    ex = ActionExecutor(kb, ms, {}, hp_potion_key="1", mp_potion_key="2")

    ex.execute({"type": "use_hp_potion"})
    assert "1" in kb.pressed


def test_executor_use_mp_potion():
    kb = FakeKeyboard()
    ms = FakeMouse()
    ex = ActionExecutor(kb, ms, {}, hp_potion_key="1", mp_potion_key="2")

    ex.execute({"type": "use_mp_potion"})
    assert "2" in kb.pressed
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_executor.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/action/executor.py
"""Translates strategy actions into keyboard/mouse operations."""

from typing import Dict, Optional

from src.utils.logger import log


class ActionExecutor:
    """Executes actions by translating them to input events."""

    def __init__(self, keyboard, mouse, skill_keys: Dict[str, str],
                 hp_potion_key: str = "1", mp_potion_key: str = "2"):
        self.kb = keyboard
        self.mouse = mouse
        self.skill_keys = skill_keys
        self.hp_potion_key = hp_potion_key
        self.mp_potion_key = mp_potion_key

    def execute(self, action: dict):
        """Execute a single action dict."""
        action_type = action.get("type")

        if action_type == "use_skill":
            self._use_skill(action)
        elif action_type == "use_hp_potion":
            self.kb.press_key(self.hp_potion_key)
        elif action_type == "use_mp_potion":
            self.kb.press_key(self.mp_potion_key)
        elif action_type == "loot_pickup":
            self._loot(action)
        elif action_type == "patrol_move":
            self._patrol_move(action)
        elif action_type == "pull_monsters":
            self._pull(action)
        elif action_type == "evade_monsters":
            self._evade(action)
        elif action_type == "revive":
            log.info("Reviving...")
        elif action_type == "go_town_buy":
            log.info("Going to town for resupply...")
        else:
            log.warning(f"Unknown action type: {action_type}")

    def _use_skill(self, action: dict):
        skill_name = action.get("skill", "")
        key = self.skill_keys.get(skill_name)
        if not key:
            log.warning(f"No key mapping for skill: {skill_name}")
            return

        target = action.get("target")
        if target:
            self.mouse.click(target["x"], target["y"])

        self.kb.press_key(key)
        log.debug(f"Used skill {skill_name} ({key})")

    def _loot(self, action: dict):
        # Pick up items by clicking near player position
        # In real implementation, would scan for item names/colors
        log.debug("Picking up loot")

    def _patrol_move(self, action: dict):
        # Move to next patrol waypoint
        log.debug("Patrol move")

    def _pull(self, action: dict):
        log.debug("Pulling monsters towards pet")

    def _evade(self, action: dict):
        log.debug("Evading monsters")

    def execute_all(self, actions: list):
        """Execute a list of actions."""
        for action in actions:
            self.execute(action)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_executor.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/action/executor.py tests/test_executor.py
git commit -m "feat: action executor bridges strategy to keyboard/mouse input"
```

---

### Task 14: Main Bot Loop

**Files:**
- Create: `src/bot.py`
- Create: `tests/test_bot.py`

**Step 1: Write the failing test**

```python
# tests/test_bot.py
"""Tests for main bot loop."""

import pytest

from src.bot import MirBot


def test_bot_init():
    bot = MirBot.__new__(MirBot)
    bot.running = False
    assert bot.running is False


def test_bot_mode_selection():
    """Test that bot can switch between fire and pet mode."""
    from src.strategy.fire_mage import build_fire_mage_fsm
    from src.strategy.pet_mage import build_pet_mage_fsm

    fire_sm = build_fire_mage_fsm()
    pet_sm = build_pet_mage_fsm()

    assert fire_sm.current_state.name == "patrol"
    assert pet_sm.current_state.name == "check_pet"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_bot.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/bot.py
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
        self.hp_mp = HpMpDetector(
            hp_color_min=np.array(self.config.colors.hp_red),
            hp_color_max=np.array(self.config.colors.hp_red_max),
            mp_color_min=np.array(self.config.colors.mp_blue),
            mp_color_max=np.array(self.config.colors.mp_blue_max),
        )
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
                time.sleep(0.1)  # ~10 ticks per second
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
        # 1. Capture screen
        frame = self.screen.capture(self.window.hwnd)
        if frame is None:
            return

        # 2. Update game state from vision
        self._update_state(frame)

        # 3. Run strategy
        ctx = {
            "game_state": self.game_state,
            "hp_threshold": self.config.player.hp_threshold,
            "mp_threshold": self.config.player.mp_threshold,
            "actions": [],
        }
        self.strategy.update(ctx)

        # 4. Execute actions
        self.executor.execute_all(ctx["actions"])

    def _update_state(self, frame: np.ndarray):
        """Update game state from a captured frame."""
        # HP/MP
        hp_region = self.screen.crop_region(frame, self.config.screen.hp_bar_region)
        mp_region = self.screen.crop_region(frame, self.config.screen.mp_bar_region)
        self.game_state.player.hp_ratio = self.hp_mp.detect_bar_ratio(hp_region, "hp")
        self.game_state.player.mp_ratio = self.hp_mp.detect_bar_ratio(mp_region, "mp")

        # Monsters
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
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_bot.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/bot.py tests/test_bot.py
git commit -m "feat: main bot loop integrating capture, vision, state, strategy, action"
```

---

### Task 15: GUI Main Window

**Files:**
- Create: `src/gui/main_window.py`

**Step 1: Write GUI implementation**

```python
# src/gui/main_window.py
"""Main GUI window for MirBot."""

import sys
import threading

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from src.bot import MirBot
from src.utils.logger import log


class BotWindow(QMainWindow):
    """Main control window for MirBot."""

    log_signal = pyqtSignal(str)

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__()
        self.config_path = config_path
        self.bot = None
        self.bot_thread = None
        self._init_ui()
        self.log_signal.connect(self._append_log)

    def _init_ui(self):
        self.setWindowTitle("MirBot - 热血传奇法师练级")
        self.setMinimumSize(500, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Status
        status_group = QGroupBox("状态")
        status_layout = QHBoxLayout(status_group)
        self.status_label = QLabel("已停止")
        self.status_label.setFont(QFont("", 14, QFont.Bold))
        self.hp_label = QLabel("HP: --%")
        self.mp_label = QLabel("MP: --%")
        self.state_label = QLabel("状态: --")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.hp_label)
        status_layout.addWidget(self.mp_label)
        status_layout.addWidget(self.state_label)
        layout.addWidget(status_group)

        # Controls
        ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["fire - 火力输出", "pet - 宝宝练级"])
        ctrl_layout.addWidget(QLabel("模式:"))
        ctrl_layout.addWidget(self.mode_combo)

        self.start_btn = QPushButton("启动")
        self.start_btn.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addWidget(ctrl_group)

        # Log
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        # Status update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(500)

    def _on_start(self):
        mode = self.mode_combo.currentText().split(" - ")[0]
        try:
            self.bot = MirBot(self.config_path)
            self.bot.set_mode(mode)
        except Exception as e:
            self._append_log(f"初始化失败: {e}")
            return

        self.bot_thread = threading.Thread(target=self.bot.start, daemon=True)
        self.bot_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("运行中")
        self._append_log(f"Bot 已启动，模式: {mode}")

    def _on_stop(self):
        if self.bot:
            self.bot.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")
        self._append_log("Bot 已停止")

    def _update_status(self):
        if self.bot and self.bot.running:
            gs = self.bot.game_state
            self.hp_label.setText(f"HP: {gs.player.hp_ratio:.0%}")
            self.mp_label.setText(f"MP: {gs.player.mp_ratio:.0%}")
            if self.bot.strategy.current_state:
                self.state_label.setText(f"状态: {self.bot.strategy.current_state.name}")

    def _append_log(self, msg: str):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


def run_gui(config_path: str = "config.yaml"):
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    window = BotWindow(config_path)
    window.show()
    sys.exit(app.exec_())
```

**Step 2: Update main.py**

```python
# main.py
"""MirBot - 热血传奇法师自动练级工具"""

import sys


def main():
    from src.gui.main_window import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 3: Commit**

```bash
git add src/gui/main_window.py main.py
git commit -m "feat: PyQt5 GUI with start/stop, mode selection, status display, and log"
```

---

### Task 16: Run All Tests & Final Verification

**Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass (approximately 22 tests)

**Step 2: Verify project structure**

```bash
find . -name "*.py" | head -30
```

**Step 3: Final commit if any cleanup needed**

```bash
git add -A
git status
# Only commit if there are changes
git commit -m "chore: final cleanup and verify all tests pass"
```

---

## Summary of Implementation Order

| Task | Module | Tests |
|------|--------|-------|
| 1 | Project scaffold | — |
| 2 | Config loader | 2 tests |
| 3 | Logger | — |
| 4 | Window manager | 2 tests |
| 5 | Screen capture | 2 tests |
| 6 | HP/MP detection | 4 tests |
| 7 | OCR monster detection | 3 tests |
| 8 | Player & game state | 7 tests |
| 9 | Keyboard/mouse/skills | 3 tests |
| 10 | State machine base | 1 test |
| 11 | Fire mage strategy | 5 tests |
| 12 | Pet mage strategy | 5 tests |
| 13 | Action executor | 3 tests |
| 14 | Main bot loop | 2 tests |
| 15 | GUI | manual test |
| 16 | Final verification | — |
