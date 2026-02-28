"""工具脚本：截取游戏窗口，在图上标出当前 hp_bar_region 和 mp_bar_region 的位置。
用法：在 Windows 上运行  python tools/find_hp_bar.py
会保存两个文件：
  - tools/screenshot.png      游戏窗口完整截图
  - tools/screenshot_marked.png  标注了 HP/MP 区域的截图
然后用画图或看图软件打开 screenshot.png，找到 HP 条的真实像素坐标。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.capture.window import WindowManager
from src.capture.screen import ScreenCapture
from src.utils.config import load_config
from PIL import Image, ImageDraw

def main():
    config = load_config("config.yaml")
    wm = WindowManager(config.game.window_title)
    if not wm.find_window():
        print("找不到游戏窗口，请确认游戏已启动")
        return

    sc = ScreenCapture()
    frame = sc.capture(wm.hwnd)
    if frame is None:
        print("截图失败")
        return

    img = Image.fromarray(frame)
    img.save("tools/screenshot.png")
    print(f"已保存截图: tools/screenshot.png ({img.size[0]}x{img.size[1]})")

    # 在截图上标注当前配置的 HP/MP 区域
    draw = ImageDraw.Draw(img)
    hp = config.screen.hp_bar_region  # [x, y, w, h]
    mp = config.screen.mp_bar_region
    # crop_region 用法是 frame[y:y+h, x:x+w]
    draw.rectangle([hp[0], hp[1], hp[0]+hp[2], hp[1]+hp[3]], outline="red", width=2)
    draw.text((hp[0], hp[1]-12), "HP region", fill="red")
    draw.rectangle([mp[0], mp[1], mp[0]+mp[2], mp[1]+mp[3]], outline="blue", width=2)
    draw.text((mp[0], mp[1]-12), "MP region", fill="blue")

    img.save("tools/screenshot_marked.png")
    print(f"已保存标注截图: tools/screenshot_marked.png")
    print(f"\n当前配置:")
    print(f"  hp_bar_region: {hp}  -> 区域 ({hp[0]},{hp[1]}) 到 ({hp[0]+hp[2]},{hp[1]+hp[3]})")
    print(f"  mp_bar_region: {mp}  -> 区域 ({mp[0]},{mp[1]}) 到 ({mp[0]+mp[2]},{mp[1]+mp[3]})")
    print(f"\n请打开 tools/screenshot.png 用画图工具查看 HP 条的实际像素坐标")
    print(f"然后修改 config.yaml 中的 hp_bar_region 和 mp_bar_region")
    print(f"格式: [x, y, width, height]")

if __name__ == "__main__":
    main()
