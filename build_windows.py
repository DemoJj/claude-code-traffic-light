#!/usr/bin/env python3
"""Windows 打包脚本：生成无控制台单文件 exe"""
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.abspath(__file__))
PyInstaller.__main__.run([
    os.path.join(ROOT, "traffic_light.py"),
    "--onefile",
    "--windowed",
    "--name=ClaudeTrafficLight",
    "--clean",
])

print("\n构建完成: dist/ClaudeTrafficLight.exe")
