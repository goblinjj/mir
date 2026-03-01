"""MirBot - 热血传奇法师自动练级工具"""

import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_mkl"] = "0"

import sys


def _disable_mkldnn():
    """Disable MKL-DNN/OneDNN in PaddlePaddle to avoid fused_conv2d errors."""
    try:
        import paddle
        paddle.set_device("cpu")
        paddle.set_flags({"FLAGS_use_mkldnn": 0})
    except Exception:
        pass


def main():
    _disable_mkldnn()
    from src.gui.main_window import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
