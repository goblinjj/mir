# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MirBot — a Python automation bot for the MMORPG "Legend of Mir" (热血传奇), targeting a 996-engine private server (圣山传说). It automates mage character leveling via screenshot analysis and simulated keyboard/mouse input (no memory reading or packet injection). Windows-targeted at runtime; development and tests run cross-platform.

## Commands

```bash
pip install -r requirements.txt   # Install dependencies
pytest                             # Run all tests (74 tests, no config file needed)
pytest tests/test_fire_mage.py     # Run a single test file
pytest -k test_name                # Run a single test by name
python main.py                     # Launch the PyQt5 GUI
```

No linter or formatter is configured.

## Architecture

**Entry point**: `main.py` → PyQt5 GUI (`src/gui/main_window.py`). Bot runs on a daemon thread; GUI polls state via QTimer.

**Core loop** (`src/bot.py` MirBot): each tick captures screen → detects HP/MP + monsters → builds a context dict → runs FSM tick → executes resulting actions.

**Key subsystems**:

| Directory | Role |
|---|---|
| `src/capture/` | Win32 background screenshot + window handle management |
| `src/vision/` | HP/MP bar detection (color ratio), monster name OCR (PaddleOCR), minimap analysis |
| `src/state/` | `PlayerState` and `GameState` dataclasses |
| `src/strategy/` | FSM engine (`base.py`) + two mode implementations + waypoint navigator |
| `src/action/` | Translates action dicts → Win32 keyboard/mouse calls; skill cooldown tracking |
| `src/gui/` | PyQt5 main window + interactive minimap widget for waypoint editing |
| `src/utils/` | YAML config loader (→ typed dataclasses), logging setup |
| `tools/` | Debug utilities (e.g. `find_hp_bar.py` for HP/MP region visualization) |

**FSM pattern**: Each `State` subclass implements `execute(ctx) -> Optional[str]` returning next state name or `None` to stay. States append action dicts (`{"type": "use_skill", ...}`) to `ctx["actions"]`; `ActionExecutor` processes them after the tick. This decouples strategy from I/O.

**Two leveling modes**:
- `fire` (`fire_mage.py`): patrol → combat → heal → loot → dead → resupply
- `pet` (`pet_mage.py`): check_pet → summon_pet → pull → evade → heal → loot → dead

**Minimap navigation system**: `MinimapAnalyzer` (`vision/minimap.py`) detects the player's white dot position and builds a walkability mask via connected-component labeling. `WaypointNavigator` (`strategy/navigator.py`) provides 8-direction discrete navigation toward waypoints with teleport recovery. The GUI's `MinimapWidget` (`gui/minimap_widget.py`) lets users visually place waypoints (left-click add, right-click remove) which are persisted to config. `PatrolState` uses waypoint navigation with rotation fallback.

**Platform stubs**: Win32 calls in capture/action modules are gated by `sys.platform != "win32"` and return early on other platforms, allowing the full test suite to run on macOS/Linux.

## Configuration

`config.yaml` → loaded by `src/utils/config.py` into a tree of `@dataclass` classes (`Config → GameConfig, PlayerConfig, SkillsConfig, LevelingConfig, PetConfig, ScreenConfig, ColorsConfig`). The loader tolerates unknown YAML keys.

Key config sections beyond the basics:
- `minimap` — region coordinates, white/black thresholds for player dot and walkability detection, arrival radius
- `patrol.waypoints` — list of `[x, y]` coordinates populated by the GUI minimap editor

## Testing

Pure unit tests with no external dependencies. Win32 calls are naturally stubbed on non-Windows. PaddleOCR falls back to `_StubOCR` when unavailable. FSM tests build context dicts directly via `make_ctx()` helpers. Action tests use inline `FakeKeyboard`/`FakeMouse` fakes.

## Design docs

- `docs/plans/2026-02-28-mir-mage-bot-design.md` — architecture design (Chinese)
- `docs/plans/2026-02-28-mir-mage-bot-plan.md` — implementation plan (Chinese)
- `docs/plans/2026-03-01-minimap-patrol-design.md` — minimap patrol design (Chinese)
- `docs/plans/2026-03-01-minimap-patrol-plan.md` — minimap patrol implementation plan (Chinese)
