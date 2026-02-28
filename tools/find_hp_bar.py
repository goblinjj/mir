"""工具脚本：截取游戏窗口，标注 HP/MP 文字区域，并测试 OCR 读取。
用法：在 Windows 上运行  python tools/find_hp_bar.py
会保存：
  - tools/screenshot.png         游戏窗口完整截图
  - tools/screenshot_marked.png  标注了 HP/MP 文字区域的截图
  - tools/hp_crop.png            HP 文字裁剪区域
  - tools/mp_crop.png            MP 文字裁剪区域
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.capture.window import GameWindow
from src.capture.screen import ScreenCapture
from src.utils.config import load_config
from src.vision.hp_mp import HpMpDetector
from PIL import Image, ImageDraw


def main():
    config = load_config("config.yaml")
    wm = GameWindow(config.game.window_title)
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

    # 标注 HP/MP 文字区域
    draw = ImageDraw.Draw(img)
    hp_t = config.screen.hp_text_region
    mp_t = config.screen.mp_text_region

    draw.rectangle([hp_t[0], hp_t[1], hp_t[0]+hp_t[2], hp_t[1]+hp_t[3]], outline="red", width=2)
    draw.text((hp_t[0], hp_t[1]-14), "HP text", fill="red")
    draw.rectangle([mp_t[0], mp_t[1], mp_t[0]+mp_t[2], mp_t[1]+mp_t[3]], outline="cyan", width=2)
    draw.text((mp_t[0], mp_t[1]-14), "MP text", fill="cyan")

    img.save("tools/screenshot_marked.png")
    print(f"已保存标注截图: tools/screenshot_marked.png")

    # 保存裁剪区域
    hp_crop = frame[hp_t[1]:hp_t[1]+hp_t[3], hp_t[0]:hp_t[0]+hp_t[2]]
    mp_crop = frame[mp_t[1]:mp_t[1]+mp_t[3], mp_t[0]:mp_t[0]+mp_t[2]]
    Image.fromarray(hp_crop).save("tools/hp_crop.png")
    Image.fromarray(mp_crop).save("tools/mp_crop.png")
    print(f"已保存裁剪: tools/hp_crop.png, tools/mp_crop.png")

    # 测试 OCR 读取
    print(f"\n当前配置:")
    print(f"  hp_text_region: {hp_t}")
    print(f"  mp_text_region: {mp_t}")

    detector = HpMpDetector()
    hp_ratio, mp_ratio = detector.detect_hp_mp(frame, hp_t, mp_t)
    print(f"\nOCR 检测结果:")
    print(f"  HP ratio: {hp_ratio:.2f}")
    print(f"  MP ratio: {mp_ratio:.2f}")

    if hp_ratio == 1.0 and mp_ratio == 1.0:
        print("\n⚠ 结果可能不准确，请检查:")
        print("  1. tools/hp_crop.png 和 mp_crop.png 是否包含正确的数字")
        print("  2. 如果区域不对，用画图打开 screenshot.png 找到数字坐标")
        print("  3. 修改 config.yaml 中的 hp_text_region / mp_text_region")
        print("     格式: [x, y, 宽度, 高度]")


if __name__ == "__main__":
    main()
