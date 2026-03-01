"""MirBot - 热血传奇法师自动练级工具"""

import os
os.environ["FLAGS_use_mkldnn"] = "0"

import sys


def main():
    from src.gui.main_window import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
