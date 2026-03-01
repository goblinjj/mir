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


def _ensure_admin():
    """Re-launch as admin if not already elevated (Windows only)."""
    if sys.platform != "win32":
        return
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin():
        return
    # Re-run this script with admin rights
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def main():
    _ensure_admin()
    _disable_mkldnn()
    from src.gui.main_window import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
