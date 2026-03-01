"""Debug tool: visualize minimap walkability mask, BFS path, and erosion.

Usage:
    python tools/debug_minimap_path.py [screenshot_path]

If no screenshot path given, uses tools/screenshot.png.
Outputs:
    tools/minimap_debug.png — walkability mask + BFS path overlay
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.utils.config import load_config
from src.vision.minimap import MinimapAnalyzer


def erode_mask(mask: np.ndarray, iterations: int = 2) -> np.ndarray:
    """Erode walkability mask to create safety margin around walls."""
    result = mask.copy()
    for _ in range(iterations):
        eroded = result.copy()
        eroded[1:, :] &= result[:-1, :]   # need walkable above
        eroded[:-1, :] &= result[1:, :]   # need walkable below
        eroded[:, 1:] &= result[:, :-1]   # need walkable left
        eroded[:, :-1] &= result[:, 1:]   # need walkable right
        result = eroded
    return result


def main():
    screenshot_path = sys.argv[1] if len(sys.argv) > 1 else "tools/screenshot.png"

    # Load config
    config = load_config("config.yaml")
    region = config.minimap.region  # [x, y, w, h]

    # Load screenshot and crop minimap
    from PIL import Image
    img = Image.open(screenshot_path)
    frame = np.array(img)
    x, y, w, h = region
    minimap = frame[y:y+h, x:x+w]

    print(f"Minimap region: {region}")
    print(f"Minimap shape: {minimap.shape}")

    # Analyze
    analyzer = MinimapAnalyzer(
        white_threshold=config.minimap.white_threshold,
        black_threshold=config.minimap.black_threshold,
    )

    player_pos = analyzer.detect_player_position(minimap)
    print(f"Player position: {player_pos}")

    raw_mask = analyzer.get_walkability_mask(minimap)
    walkable_pct = np.sum(raw_mask) / raw_mask.size * 100
    print(f"Raw walkable: {walkable_pct:.1f}%")

    eroded = erode_mask(raw_mask, iterations=2)
    eroded_pct = np.sum(eroded) / eroded.size * 100
    print(f"Eroded walkable: {eroded_pct:.1f}%")

    # Waypoints
    waypoints = config.patrol.waypoints
    print(f"Waypoints: {waypoints}")

    # Create visualization: 3 panels side by side
    # 1. Original minimap  2. Raw mask  3. Eroded mask + path
    scale = 3  # upscale for visibility
    panel_w = w * scale
    panel_h = h * scale

    canvas = np.zeros((panel_h, panel_w * 3, 3), dtype=np.uint8)

    # Panel 1: original minimap (upscaled)
    for py in range(h):
        for px in range(w):
            for dy in range(scale):
                for dx in range(scale):
                    canvas[py*scale+dy, px*scale+dx] = minimap[py, px]

    # Panel 2: raw walkability mask
    for py in range(h):
        for px in range(w):
            color = (200, 200, 200) if raw_mask[py, px] else (30, 0, 0)
            for dy in range(scale):
                for dx in range(scale):
                    canvas[py*scale+dy, panel_w + px*scale+dx] = color

    # Panel 3: eroded mask
    for py in range(h):
        for px in range(w):
            color = (200, 200, 200) if eroded[py, px] else (30, 0, 0)
            for dy in range(scale):
                for dx in range(scale):
                    canvas[py*scale+dy, 2*panel_w + px*scale+dx] = color

    # Draw BFS path on panel 3
    if player_pos and waypoints:
        target = waypoints[0]
        # Path on raw mask
        raw_path = MinimapAnalyzer.find_path(raw_mask, player_pos, (target[0], target[1]))
        print(f"Raw path length: {len(raw_path)}")
        # Path on eroded mask
        eroded_path = MinimapAnalyzer.find_path(eroded, player_pos, (target[0], target[1]))
        print(f"Eroded path length: {len(eroded_path)}")

        # Draw raw path on panel 2 (blue)
        for (px, py) in raw_path:
            for dy in range(scale):
                for dx in range(scale):
                    canvas[py*scale+dy, panel_w + px*scale+dx] = (0, 100, 255)

        # Draw eroded path on panel 3 (green)
        for (px, py) in eroded_path:
            for dy in range(scale):
                for dx in range(scale):
                    canvas[py*scale+dy, 2*panel_w + px*scale+dx] = (0, 255, 100)

    # Draw player position on all panels (red dot)
    if player_pos:
        px, py = player_pos
        for panel in range(3):
            for dy in range(-2*scale, 2*scale+1):
                for dx in range(-2*scale, 2*scale+1):
                    ny = py*scale + dy
                    nx = panel * panel_w + px*scale + dx
                    if 0 <= ny < panel_h and panel*panel_w <= nx < (panel+1)*panel_w:
                        canvas[ny, nx] = (255, 0, 0)

    # Draw waypoints on all panels (yellow dots)
    for wp in (waypoints or []):
        wpx, wpy = wp
        for panel in range(3):
            for dy in range(-2*scale, 2*scale+1):
                for dx in range(-2*scale, 2*scale+1):
                    ny = wpy*scale + dy
                    nx = panel * panel_w + wpx*scale + dx
                    if 0 <= ny < panel_h and panel*panel_w <= nx < (panel+1)*panel_w:
                        canvas[ny, nx] = (255, 255, 0)

    out_path = "tools/minimap_debug.png"
    Image.fromarray(canvas).save(out_path)
    print(f"\nSaved debug image to {out_path}")
    print("Left: original minimap | Middle: raw mask + path (blue) | Right: eroded mask + path (green)")


if __name__ == "__main__":
    main()
