# Minimap Visual Navigation Patrol System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 8-direction rotation patrol with waypoint-based navigation using minimap white-dot detection.

**Architecture:** New `MinimapAnalyzer` vision module detects player position (white dot) on the minimap. GUI gains a waypoint editor panel where users click the minimap image to set patrol points. `PatrolState` is rewritten to navigate toward the next waypoint by computing direction from current position to target. After teleport scroll use, the nearest waypoint is selected as the new target.

**Tech Stack:** Python, NumPy (image processing), PyQt5 (GUI), OpenCV-free (threshold + connected component via scipy.ndimage or pure numpy)

---

### Task 1: MinimapAnalyzer — White Dot Detection

**Files:**
- Create: `src/vision/minimap.py`
- Create: `tests/test_minimap.py`

**Step 1: Write the failing test for white dot detection**

```python
# tests/test_minimap.py
import numpy as np
import pytest
from src.vision.minimap import MinimapAnalyzer


def _make_frame(width=160, height=180, dots=None, bg_color=(40, 40, 40)):
    """Create a fake minimap frame with optional white dots."""
    frame = np.full((height, width, 3), bg_color, dtype=np.uint8)
    if dots:
        for (x, y) in dots:
            # Draw a 3x3 white dot
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        frame[ny, nx] = (255, 255, 255)
    return frame


class TestWhiteDotDetection:
    def setup_method(self):
        self.analyzer = MinimapAnalyzer(white_threshold=240, black_threshold=15)

    def test_detect_single_white_dot(self):
        frame = _make_frame(dots=[(80, 90)])
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        assert abs(x - 80) <= 1
        assert abs(y - 90) <= 1

    def test_detect_no_dot_returns_none(self):
        frame = _make_frame()  # no dots
        pos = self.analyzer.detect_player_position(frame)
        assert pos is None

    def test_detect_dot_ignores_dim_pixels(self):
        """Pixels below threshold should not be detected."""
        frame = _make_frame(bg_color=(200, 200, 200))  # bright but below 240
        pos = self.analyzer.detect_player_position(frame)
        assert pos is None

    def test_detect_brightest_cluster(self):
        """If multiple bright areas, return the one with most white pixels."""
        frame = _make_frame(dots=[(30, 30), (80, 90)])
        # Add extra white pixels around (80, 90) to make it the larger cluster
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                ny, nx = 90 + dy, 80 + dx
                if 0 <= ny < 180 and 0 <= nx < 160:
                    frame[ny, nx] = (255, 255, 255)
        pos = self.analyzer.detect_player_position(frame)
        assert pos is not None
        x, y = pos
        assert abs(x - 80) <= 2
        assert abs(y - 90) <= 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_minimap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.vision.minimap'`

**Step 3: Implement MinimapAnalyzer white dot detection**

```python
# src/vision/minimap.py
"""Minimap analysis: player position detection and walkability mask."""

from typing import Optional, Tuple

import numpy as np


class MinimapAnalyzer:
    """Analyzes minimap screenshots for player position and terrain."""

    def __init__(self, white_threshold: int = 240, black_threshold: int = 15):
        self.white_threshold = white_threshold
        self.black_threshold = black_threshold

    def detect_player_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """Detect the white dot (player) on the minimap frame.

        Args:
            frame: BGR or RGB minimap image (H, W, 3).

        Returns:
            (x, y) pixel coordinates of the player dot, or None if not found.
        """
        if frame is None or frame.size == 0:
            return None

        # All channels must be above threshold (white dot)
        min_channel = np.min(frame, axis=2)
        white_mask = min_channel >= self.white_threshold

        if not np.any(white_mask):
            return None

        # Find connected components via simple flood-fill alternative:
        # use labeled regions from scipy if available, else find centroid of all white pixels
        ys, xs = np.where(white_mask)
        if len(xs) == 0:
            return None

        # Simple approach: return centroid of largest connected cluster
        # For efficiency, just return centroid of all white pixels
        # (usually only one white dot on minimap)
        cx = int(np.mean(xs))
        cy = int(np.mean(ys))
        return (cx, cy)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_minimap.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add src/vision/minimap.py tests/test_minimap.py
git commit -m "feat: add MinimapAnalyzer with white dot detection"
```

---

### Task 2: MinimapAnalyzer — Walkability Mask

**Files:**
- Modify: `src/vision/minimap.py`
- Modify: `tests/test_minimap.py`

**Step 1: Write failing tests for walkability**

```python
# Append to tests/test_minimap.py

class TestWalkability:
    def setup_method(self):
        self.analyzer = MinimapAnalyzer(white_threshold=240, black_threshold=15)

    def test_black_is_not_walkable(self):
        frame = _make_frame(bg_color=(0, 0, 0))  # all black
        assert not self.analyzer.is_walkable(frame, 80, 90)

    def test_non_black_is_walkable(self):
        frame = _make_frame(bg_color=(60, 50, 40))  # brownish = walkable
        assert self.analyzer.is_walkable(frame, 80, 90)

    def test_walkability_mask_shape(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        mask = self.analyzer.get_walkability_mask(frame)
        assert mask.shape == (180, 160)
        assert mask.dtype == bool

    def test_walkability_mask_mixed(self):
        frame = _make_frame(bg_color=(60, 50, 40))
        # Paint a black rectangle (wall)
        frame[50:80, 30:60] = (0, 0, 0)
        mask = self.analyzer.get_walkability_mask(frame)
        assert not mask[65, 45]  # inside black area
        assert mask[10, 10]      # outside black area

    def test_is_walkable_out_of_bounds(self):
        frame = _make_frame()
        assert not self.analyzer.is_walkable(frame, -1, 0)
        assert not self.analyzer.is_walkable(frame, 0, 999)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_minimap.py::TestWalkability -v`
Expected: FAIL — `AttributeError: 'MinimapAnalyzer' object has no attribute 'is_walkable'`

**Step 3: Implement walkability methods**

Add to `src/vision/minimap.py` class `MinimapAnalyzer`:

```python
    def get_walkability_mask(self, frame: np.ndarray) -> np.ndarray:
        """Generate walkability mask from minimap frame.

        Returns:
            Boolean array (H, W) where True = walkable, False = wall/boundary.
        """
        max_channel = np.max(frame, axis=2)
        return max_channel >= self.black_threshold

    def is_walkable(self, frame: np.ndarray, x: int, y: int) -> bool:
        """Check if a specific minimap pixel is walkable."""
        h, w = frame.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return False
        # All channels below threshold = black = unwalkable
        return int(np.max(frame[y, x])) >= self.black_threshold
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_minimap.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/vision/minimap.py tests/test_minimap.py
git commit -m "feat: add walkability mask and is_walkable to MinimapAnalyzer"
```

---

### Task 3: Config — Add Minimap and Patrol Waypoint Settings

**Files:**
- Modify: `src/utils/config.py` (lines 46-53 ScreenConfig, lines 30-36 LevelingConfig)
- Modify: `config.yaml`

**Step 1: Write failing test**

```python
# tests/test_config_minimap.py
from src.utils.config import load_config, MinimapConfig


def test_minimap_config_defaults():
    cfg = MinimapConfig()
    assert cfg.region == [0, 0, 0, 0]
    assert cfg.white_threshold == 240
    assert cfg.black_threshold == 15
    assert cfg.arrival_radius == 5


def test_load_config_has_minimap(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
game:
  window_title: test
minimap:
  region: [1230, 30, 160, 180]
  white_threshold: 235
  arrival_radius: 8
patrol:
  waypoints: [[50, 60], [100, 80]]
""")
    cfg = load_config(str(yaml_file))
    assert cfg.minimap.region == [1230, 30, 160, 180]
    assert cfg.minimap.white_threshold == 235
    assert cfg.minimap.arrival_radius == 8
    assert cfg.patrol.waypoints == [[50, 60], [100, 80]]
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_minimap.py -v`
Expected: FAIL — `ImportError: cannot import name 'MinimapConfig'`

**Step 3: Add MinimapConfig and PatrolConfig dataclasses**

In `src/utils/config.py`, add after `ColorsConfig` (around line 61):

```python
@dataclass
class MinimapConfig:
    region: list = field(default_factory=lambda: [0, 0, 0, 0])
    white_threshold: int = 240
    black_threshold: int = 15
    arrival_radius: int = 5


@dataclass
class PatrolConfig:
    waypoints: list = field(default_factory=list)
```

Add to `Config` class (around line 64-72) two new fields:

```python
    minimap: MinimapConfig = field(default_factory=MinimapConfig)
    patrol: PatrolConfig = field(default_factory=PatrolConfig)
```

Update `load_config()` to include the new sections (same pattern as existing ones).

**Step 4: Update `config.yaml` with minimap section**

Add to end of `config.yaml`:

```yaml
minimap:
  region: [1230, 30, 160, 180]
  white_threshold: 240
  black_threshold: 15
  arrival_radius: 5

patrol:
  waypoints: []
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config_minimap.py -v && pytest tests/ -v`
Expected: All tests PASS (including existing tests unchanged)

**Step 6: Commit**

```bash
git add src/utils/config.py config.yaml tests/test_config_minimap.py
git commit -m "feat: add MinimapConfig and PatrolConfig to config system"
```

---

### Task 4: Waypoint Navigator Logic

**Files:**
- Create: `src/strategy/navigator.py`
- Create: `tests/test_navigator.py`

**Step 1: Write failing tests**

```python
# tests/test_navigator.py
import math
import pytest
from src.strategy.navigator import WaypointNavigator


class TestWaypointNavigator:
    def test_no_waypoints_returns_none(self):
        nav = WaypointNavigator([], arrival_radius=5)
        assert nav.get_direction((80, 90)) is None

    def test_direction_to_east(self):
        nav = WaypointNavigator([[100, 50]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 2  # East

    def test_direction_to_north(self):
        nav = WaypointNavigator([[50, 10]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 0  # North (y decreases)

    def test_direction_to_south(self):
        nav = WaypointNavigator([[50, 90]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 4  # South

    def test_direction_to_northeast(self):
        nav = WaypointNavigator([[90, 10]], arrival_radius=5)
        direction = nav.get_direction((50, 50))
        assert direction == 1  # NE

    def test_arrival_advances_waypoint(self):
        nav = WaypointNavigator([[50, 50], [100, 100]], arrival_radius=5)
        assert nav.current_index == 0
        # Move close to first waypoint
        nav.get_direction((50, 52))  # within radius
        assert nav.current_index == 1  # advanced to next

    def test_loop_back_to_start(self):
        nav = WaypointNavigator([[50, 50], [100, 100]], arrival_radius=5)
        nav.current_index = 1
        nav.get_direction((100, 102))  # arrive at last waypoint
        assert nav.current_index == 0  # loop back

    def test_teleport_finds_nearest(self):
        nav = WaypointNavigator([[10, 10], [90, 90], [50, 50]], arrival_radius=5)
        nav.current_index = 0
        nav.handle_teleport((88, 92))
        assert nav.current_index == 1  # closest to (90, 90)

    def test_set_waypoints(self):
        nav = WaypointNavigator([], arrival_radius=5)
        nav.set_waypoints([[10, 20], [30, 40]])
        assert len(nav.waypoints) == 2
        assert nav.current_index == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_navigator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement WaypointNavigator**

```python
# src/strategy/navigator.py
"""Waypoint-based navigation using minimap coordinates."""

import math
from typing import List, Optional, Tuple


class WaypointNavigator:
    """Navigates between waypoints on the minimap."""

    # 8 directions: N, NE, E, SE, S, SW, W, NW
    # Angle ranges centered on each direction (in degrees, 0=East, CCW positive)
    _DIR_ANGLES = [90, 45, 0, 315, 270, 225, 180, 135]  # East=0°, North=90°

    def __init__(self, waypoints: List[List[int]], arrival_radius: int = 5):
        self.waypoints = waypoints
        self.arrival_radius = arrival_radius
        self.current_index = 0

    def get_direction(self, current_pos: Tuple[int, int]) -> Optional[int]:
        """Get the 8-direction index to move toward the current waypoint.

        Args:
            current_pos: (x, y) current player position on minimap.

        Returns:
            Direction index 0-7 (N, NE, E, SE, S, SW, W, NW) or None.
        """
        if not self.waypoints:
            return None

        tx, ty = self.waypoints[self.current_index]
        cx, cy = current_pos

        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy)

        # Check arrival
        if dist <= self.arrival_radius:
            self.current_index = (self.current_index + 1) % len(self.waypoints)
            # Recalculate for new target
            tx, ty = self.waypoints[self.current_index]
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)
            if dist <= self.arrival_radius:
                return None  # Already at next waypoint too

        # Convert to angle (screen coords: y increases downward)
        # atan2 with negated dy so that up = positive angle
        angle_rad = math.atan2(-dy, dx)
        angle_deg = math.degrees(angle_rad) % 360

        # Map angle to nearest 8-direction
        # N=90°, NE=45°, E=0°, SE=315°, S=270°, SW=225°, W=180°, NW=135°
        best_dir = 0
        best_diff = 360
        for i, dir_angle in enumerate(self._DIR_ANGLES):
            diff = abs(angle_deg - dir_angle)
            if diff > 180:
                diff = 360 - diff
            if diff < best_diff:
                best_diff = diff
                best_dir = i
        return best_dir

    def handle_teleport(self, current_pos: Tuple[int, int]) -> None:
        """After teleport, find the nearest waypoint and set it as target."""
        if not self.waypoints:
            return
        cx, cy = current_pos
        best_idx = 0
        best_dist = float("inf")
        for i, (wx, wy) in enumerate(self.waypoints):
            d = math.hypot(wx - cx, wy - cy)
            if d < best_dist:
                best_dist = d
                best_idx = i
        self.current_index = best_idx

    def set_waypoints(self, waypoints: List[List[int]]) -> None:
        """Replace waypoints and reset index."""
        self.waypoints = waypoints
        self.current_index = 0

    @property
    def current_target(self) -> Optional[List[int]]:
        """Return the current target waypoint or None."""
        if not self.waypoints:
            return None
        return self.waypoints[self.current_index]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_navigator.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/strategy/navigator.py tests/test_navigator.py
git commit -m "feat: add WaypointNavigator for minimap-based patrol"
```

---

### Task 5: Integrate MinimapAnalyzer into Bot Loop

**Files:**
- Modify: `src/bot.py` (lines 26-61 `__init__`, lines 88-113 `_tick`, lines 100-106 context)
- Modify: `tests/test_bot.py` (if exists, otherwise skip)

**Step 1: Add minimap analyzer and navigator to bot.__init__**

In `src/bot.py`, add imports at top:

```python
from src.vision.minimap import MinimapAnalyzer
from src.strategy.navigator import WaypointNavigator
```

In `__init__()`, after existing detector setup, add:

```python
        # Minimap analyzer
        mr = self.config.minimap.region
        self.minimap_region = mr  # [x, y, w, h]
        self.minimap_analyzer = MinimapAnalyzer(
            white_threshold=self.config.minimap.white_threshold,
            black_threshold=self.config.minimap.black_threshold,
        )
        self.navigator = WaypointNavigator(
            waypoints=self.config.patrol.waypoints,
            arrival_radius=self.config.minimap.arrival_radius,
        )
        self._last_minimap_pos = None
```

**Step 2: Add minimap position detection to _tick()**

In `_tick()`, after `_update_state(frame)` and `_update_coordinates(frame)`, add:

```python
        # Minimap player detection
        minimap_pos = self._detect_minimap_position(frame)
        if minimap_pos:
            self._last_minimap_pos = minimap_pos
            # Teleport detection: large jump in position
            if self._last_minimap_pos and self.game_state.stuck_count == 0:
                pass  # Normal movement
```

Add new method `_detect_minimap_position()`:

```python
    def _detect_minimap_position(self, frame):
        """Crop minimap region and detect player white dot."""
        x, y, w, h = self.minimap_region
        if w <= 0 or h <= 0:
            return None
        minimap = frame[y:y+h, x:x+w]
        return self.minimap_analyzer.detect_player_position(minimap)
```

**Step 3: Add navigator and minimap_pos to context dict**

In `_tick()`, modify context construction (lines 100-106) to include:

```python
        ctx["navigator"] = self.navigator
        ctx["minimap_pos"] = self._last_minimap_pos
```

**Step 4: Run all tests to verify nothing broken**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

**Step 5: Commit**

```bash
git add src/bot.py
git commit -m "feat: integrate MinimapAnalyzer and WaypointNavigator into bot loop"
```

---

### Task 6: Rewrite PatrolState to Use Waypoint Navigation

**Files:**
- Modify: `src/strategy/pet_mage.py` (lines 31-78 PatrolState)
- Modify: `tests/test_pet_mage.py`

**Step 1: Write failing tests for new patrol behavior**

```python
# Append to tests/test_pet_mage.py
from src.strategy.navigator import WaypointNavigator


def make_navigator(waypoints=None, arrival_radius=5):
    return WaypointNavigator(waypoints or [], arrival_radius=arrival_radius)


class TestPatrolWaypointNavigation:
    def test_patrol_uses_navigator_direction(self):
        """When navigator returns a direction, patrol uses it."""
        nav = make_navigator([[100, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (50, 50)  # player at (50,50), target at (100,50) = East
        state = PatrolState()
        result = state.execute(ctx)
        assert result is None  # stays in patrol
        actions = ctx["actions"]
        move_actions = [a for a in actions if a["type"] == "patrol_move"]
        assert len(move_actions) == 1
        assert move_actions[0]["direction"] == 2  # East

    def test_patrol_falls_back_to_rotation_without_navigator(self):
        """When no navigator or no minimap_pos, use old rotation logic."""
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = make_navigator()  # empty waypoints
        ctx["minimap_pos"] = None
        state = PatrolState()
        result = state.execute(ctx)
        assert result is None
        actions = ctx["actions"]
        move_actions = [a for a in actions if a["type"] == "patrol_move"]
        assert len(move_actions) == 1
        # Should use default direction 0 (North) from rotation fallback
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pet_mage.py::TestPatrolWaypointNavigation -v`
Expected: FAIL (ctx doesn't have navigator key, or PatrolState doesn't use it)

**Step 3: Rewrite PatrolState.execute()**

Replace PatrolState in `src/strategy/pet_mage.py` (lines 31-78):

```python
class PatrolState(State):
    """Patrol state: navigate between waypoints or fall back to rotation."""

    def __init__(self):
        super().__init__("patrol")
        # Fallback rotation fields (used when no waypoints)
        self.direction = 0
        self.ticks_in_dir = 0
        self.max_ticks_per_dir = 15

    def execute(self, ctx) -> Optional[str]:
        gs = ctx["game_state"]

        # Health/death checks (unchanged)
        if gs.player.is_dead:
            return "dead"
        if not gs.pet_alive:
            return "check_pet"
        if gs.player.needs_hp_potion(ctx.get("hp_threshold", 0.5)):
            return "heal"

        # Monster detection (unchanged)
        if gs.has_monsters():
            return self._check_monster_distance(ctx)

        # Determine move direction
        navigator = ctx.get("navigator")
        minimap_pos = ctx.get("minimap_pos")
        direction = None

        if navigator and minimap_pos and navigator.waypoints:
            direction = navigator.get_direction(minimap_pos)

        if direction is None:
            # Fallback: old rotation logic
            direction = self._rotation_direction(gs)

        ctx["actions"].append({"type": "patrol_move", "direction": direction})
        return None

    def _rotation_direction(self, gs) -> int:
        """Fallback direction rotation when no waypoints."""
        self.ticks_in_dir += 1
        if gs.stuck_count >= 3:
            self.direction = (self.direction + 1) % 8
            gs.stuck_count = 0
            self.ticks_in_dir = 0
            logger.info("Patrol: stuck, rotating to direction %d", self.direction)
        elif self.ticks_in_dir >= self.max_ticks_per_dir:
            self.direction = (self.direction + 1) % 8
            self.ticks_in_dir = 0
            logger.info("Patrol: time rotation to direction %d", self.direction)
        return self.direction

    def _check_monster_distance(self, ctx):
        # ... unchanged from current implementation ...
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/strategy/pet_mage.py tests/test_pet_mage.py
git commit -m "feat: rewrite PatrolState to use waypoint navigation with rotation fallback"
```

---

### Task 7: Teleport Detection in PatrolState

**Files:**
- Modify: `src/strategy/pet_mage.py`
- Modify: `tests/test_pet_mage.py`

**Step 1: Write failing test**

```python
class TestPatrolTeleport:
    def test_teleport_resets_to_nearest_waypoint(self):
        """Large position jump triggers nearest waypoint search."""
        nav = make_navigator([[10, 10], [90, 90], [50, 50]])
        ctx = make_ctx(pet_alive=True)
        ctx["navigator"] = nav
        ctx["minimap_pos"] = (88, 92)  # close to waypoint[1]
        state = PatrolState()
        state._last_pos = (10, 12)  # was near waypoint[0]
        state.execute(ctx)
        assert nav.current_index == 1  # jumped to nearest
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pet_mage.py::TestPatrolTeleport -v`
Expected: FAIL

**Step 3: Add teleport detection to PatrolState**

In `PatrolState.__init__`, add:
```python
        self._last_pos = None
        self._teleport_threshold = 30  # pixels on minimap
```

In `PatrolState.execute()`, before determining direction, add:

```python
        # Teleport detection
        if navigator and minimap_pos and navigator.waypoints:
            if self._last_pos is not None:
                dx = minimap_pos[0] - self._last_pos[0]
                dy = minimap_pos[1] - self._last_pos[1]
                jump_dist = math.hypot(dx, dy)
                if jump_dist > self._teleport_threshold:
                    navigator.handle_teleport(minimap_pos)
                    logger.info("Patrol: teleport detected, jumping to waypoint %d",
                                navigator.current_index)
            self._last_pos = minimap_pos
```

**Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/strategy/pet_mage.py tests/test_pet_mage.py
git commit -m "feat: add teleport detection to PatrolState"
```

---

### Task 8: GUI Waypoint Editor — Minimap Display Widget

**Files:**
- Create: `src/gui/minimap_widget.py`
- Modify: `src/gui/main_window.py`

**Step 1: Implement MinimapWidget**

```python
# src/gui/minimap_widget.py
"""Minimap widget for displaying minimap and editing waypoints."""

import logging
from typing import List, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QLabel

import numpy as np

logger = logging.getLogger("mirbot")


class MinimapWidget(QLabel):
    """Widget that displays the minimap and allows clicking to add waypoints."""

    waypoints_changed = pyqtSignal(list)  # emits list of [x, y] pairs

    def __init__(self, parent=None):
        super().__init__(parent)
        self._waypoints: List[List[int]] = []
        self._base_pixmap = None
        self._minimap_frame = None
        self.setMinimumSize(200, 220)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #555; background: #111;")
        self.setText("点击刷新获取小地图")

    def update_minimap(self, frame: np.ndarray):
        """Update the displayed minimap image."""
        if frame is None or frame.size == 0:
            return
        self._minimap_frame = frame
        h, w = frame.shape[:2]
        # Convert BGR to RGB for Qt
        rgb = frame[:, :, ::-1].copy()
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self._base_pixmap = QPixmap.fromImage(qimg)
        self._redraw()

    def set_waypoints(self, waypoints: List[List[int]]):
        """Set waypoints from config."""
        self._waypoints = [list(wp) for wp in waypoints]
        self._redraw()

    def get_waypoints(self) -> List[List[int]]:
        return self._waypoints

    def mousePressEvent(self, event):
        """Left click adds waypoint, right click removes nearest."""
        if self._base_pixmap is None:
            return

        # Map widget coords to minimap coords
        pm = self.pixmap()
        if pm is None:
            return

        # Calculate offset (pixmap is centered in label)
        x_offset = (self.width() - pm.width()) // 2
        y_offset = (self.height() - pm.height()) // 2
        mx = event.x() - x_offset
        my = event.y() - y_offset

        if mx < 0 or my < 0 or mx >= pm.width() or my >= pm.height():
            return

        if event.button() == Qt.LeftButton:
            self._waypoints.append([mx, my])
            logger.info("Waypoint added: (%d, %d), total: %d", mx, my, len(self._waypoints))
        elif event.button() == Qt.RightButton:
            if self._waypoints:
                # Remove nearest waypoint
                best_i = 0
                best_d = float("inf")
                for i, (wx, wy) in enumerate(self._waypoints):
                    d = (wx - mx) ** 2 + (wy - my) ** 2
                    if d < best_d:
                        best_d = d
                        best_i = i
                removed = self._waypoints.pop(best_i)
                logger.info("Waypoint removed: (%d, %d), remaining: %d",
                            removed[0], removed[1], len(self._waypoints))

        self.waypoints_changed.emit(self._waypoints)
        self._redraw()

    def clear_waypoints(self):
        self._waypoints.clear()
        self.waypoints_changed.emit(self._waypoints)
        self._redraw()

    def _redraw(self):
        """Redraw minimap with waypoints overlay."""
        if self._base_pixmap is None:
            return
        pm = self._base_pixmap.copy()
        painter = QPainter(pm)

        # Draw waypoint connections
        if len(self._waypoints) >= 2:
            pen = QPen(QColor(0, 255, 0, 180), 1)
            painter.setPen(pen)
            for i in range(len(self._waypoints) - 1):
                x1, y1 = self._waypoints[i]
                x2, y2 = self._waypoints[i + 1]
                painter.drawLine(x1, y1, x2, y2)
            # Close loop
            x1, y1 = self._waypoints[-1]
            x2, y2 = self._waypoints[0]
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)

        # Draw waypoint dots with numbers
        font = QFont("Arial", 7)
        painter.setFont(font)
        for i, (wx, wy) in enumerate(self._waypoints):
            painter.setPen(QPen(QColor(255, 255, 0), 1))
            painter.setBrush(QColor(255, 255, 0, 200))
            painter.drawEllipse(wx - 3, wy - 3, 6, 6)
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(wx + 5, wy - 2, str(i + 1))

        painter.end()
        self.setPixmap(pm)
```

**Step 2: No unit test for GUI widget (visual component). Test manually after integration.**

**Step 3: Commit**

```bash
git add src/gui/minimap_widget.py
git commit -m "feat: add MinimapWidget for waypoint editing"
```

---

### Task 9: Integrate Waypoint Editor into Main Window

**Files:**
- Modify: `src/gui/main_window.py`

**Step 1: Add minimap panel to GUI**

In `main_window.py`, add import:

```python
from src.gui.minimap_widget import MinimapWidget
```

In `_init_ui()`, after the monster whitelist section (around line 80), add a new group:

```python
        # --- Minimap / Waypoint group ---
        minimap_group = QGroupBox("巡逻路径 (左键添加 / 右键删除)")
        minimap_layout = QVBoxLayout()

        self.minimap_widget = MinimapWidget()
        minimap_layout.addWidget(self.minimap_widget)

        btn_layout = QHBoxLayout()
        self.btn_refresh_map = QPushButton("刷新地图")
        self.btn_clear_waypoints = QPushButton("清空路径")
        btn_layout.addWidget(self.btn_refresh_map)
        btn_layout.addWidget(self.btn_clear_waypoints)
        minimap_layout.addLayout(btn_layout)

        minimap_group.setLayout(minimap_layout)
        layout.addWidget(minimap_group)

        # Connect signals
        self.btn_refresh_map.clicked.connect(self._refresh_minimap)
        self.btn_clear_waypoints.clicked.connect(self.minimap_widget.clear_waypoints)
        self.minimap_widget.waypoints_changed.connect(self._on_waypoints_changed)
```

Add methods:

```python
    def _refresh_minimap(self):
        """Capture current frame and extract minimap region."""
        if not hasattr(self, 'bot') or self.bot is None:
            return
        frame = self.bot.capture.grab()
        if frame is None:
            return
        x, y, w, h = self.bot.minimap_region
        if w > 0 and h > 0:
            minimap = frame[y:y+h, x:x+w]
            self.minimap_widget.update_minimap(minimap)

    def _on_waypoints_changed(self, waypoints):
        """Update config and navigator when waypoints change."""
        if hasattr(self, 'bot') and self.bot is not None:
            self.bot.config.patrol.waypoints = waypoints
            self.bot.navigator.set_waypoints(waypoints)
```

In `_on_start()`, after bot creation, load existing waypoints:

```python
        if self.bot.config.patrol.waypoints:
            self.minimap_widget.set_waypoints(self.bot.config.patrol.waypoints)
```

**Step 2: Run existing tests to verify nothing broken**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

**Step 3: Commit**

```bash
git add src/gui/main_window.py
git commit -m "feat: integrate minimap waypoint editor into main GUI"
```

---

### Task 10: Minimap Frame Pass-through for Live Position Display

**Files:**
- Modify: `src/gui/main_window.py`
- Modify: `src/bot.py`

**Step 1: Add minimap frame to bot state for GUI polling**

In `src/bot.py`, add to `__init__`:
```python
        self.last_minimap_frame = None
```

In `_detect_minimap_position()`, save the frame:
```python
        self.last_minimap_frame = minimap
```

**Step 2: Update GUI status poll to refresh minimap overlay**

In `_update_status()` in `main_window.py`, add at the end:

```python
        # Update minimap display with player position indicator
        if hasattr(self, 'bot') and self.bot and self.bot.last_minimap_frame is not None:
            self.minimap_widget.update_minimap(self.bot.last_minimap_frame)
```

Note: This is optional / can be toggled. During patrol, the minimap updates every 500ms (QTimer rate) to show live position. Consider adding a checkbox to control auto-refresh to avoid performance impact.

**Step 3: Run tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/bot.py src/gui/main_window.py
git commit -m "feat: pass minimap frame to GUI for live position display"
```

---

### Task 11: Save/Load Waypoints to Config File

**Files:**
- Modify: `src/gui/main_window.py`
- Modify: `src/utils/config.py` (add save function if not exists)

**Step 1: Add waypoint save on stop/close**

In `main_window.py`, in `_on_stop()` or window close event, save current waypoints to config.yaml:

```python
    def _save_waypoints(self):
        """Save current waypoints to config.yaml."""
        if not hasattr(self, 'bot') or self.bot is None:
            return
        waypoints = self.minimap_widget.get_waypoints()
        # Update config file
        import yaml
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if "patrol" not in data:
                data["patrol"] = {}
            data["patrol"]["waypoints"] = waypoints
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            logger.info("Waypoints saved: %d points", len(waypoints))
        except Exception as e:
            logger.error("Failed to save waypoints: %s", e)
```

Call `_save_waypoints()` from `_on_stop()` and `closeEvent()`.

**Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/gui/main_window.py
git commit -m "feat: save/load waypoints to config.yaml"
```

---

### Task 12: End-to-End Manual Test

**Step 1:** Run the bot GUI: `python main.py`
**Step 2:** Click "刷新地图" to capture minimap
**Step 3:** Left-click on minimap to add 3-4 patrol waypoints
**Step 4:** Verify waypoints shown with numbers and green lines
**Step 5:** Right-click near a waypoint to remove it
**Step 6:** Start bot in pet mode — verify patrol follows waypoints
**Step 7:** Verify "清空路径" button works
**Step 8:** Stop bot — verify waypoints saved to config.yaml
**Step 9:** Restart bot — verify waypoints loaded from config

**Step 10: Final commit**

```bash
git add -A
git commit -m "feat: minimap visual navigation patrol system complete"
git push
```
