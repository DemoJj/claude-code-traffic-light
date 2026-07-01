"""平台检测与运行时环境"""
import os
import sys

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


def setup_frozen_path():
    """PyInstaller 打包后切换到 exe 所在目录"""
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
