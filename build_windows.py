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
if not os.path.isfile(ICON_PATH) or os.path.getsize(ICON_PATH) < 1024:
    print(f"错误: 图标文件无效 ({ICON_PATH})", file=sys.stderr)
    sys.exit(1)
print(f"图标已生成: {ICON_PATH} ({os.path.getsize(ICON_PATH)} bytes)")

PyInstaller.__main__.run([
    os.path.join(ROOT, "traffic_light.py"),
    "--onefile",
    "--windowed",
    "--noconfirm",
    "--clean",
    "--name=ClaudeTrafficLight",
    f"--icon={ICON_PATH}",
    f"--distpath={os.path.join(ROOT, 'dist')}",
    f"--workpath={os.path.join(ROOT, 'build')}",
    f"--specpath={ROOT}",
])

print("\n构建完成: dist/ClaudeTrafficLight.exe")
