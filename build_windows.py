#!/usr/bin/env python3
"""Windows 打包脚本：生成无控制台单文件 exe"""
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(ROOT, "traffic_light.ico")

sys.path.insert(0, ROOT)
from traffic_light import save_tray_icon_ico

print("正在生成托盘图标 traffic_light.ico ...")
save_tray_icon_ico(ICON_PATH)

PyInstaller.__main__.run([
    os.path.join(ROOT, "traffic_light.py"),
    "--onefile",
    "--windowed",
    "--name=ClaudeTrafficLight",
    f"--icon={ICON_PATH}",
    "--clean",
])

print("\n构建完成: dist/ClaudeTrafficLight.exe")
