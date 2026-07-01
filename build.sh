#!/bin/bash
# macOS 打包脚本：将 main.py 打包为 ClaudeTrafficLight.app
# 用法：bash build.sh
# 依赖：Python 3.9+、PyInstaller（见 requirements.txt）
# 产出：dist/ClaudeTrafficLight.app（无控制台窗口的 .app 应用包）

set -e  # 任一步骤失败则立即退出

echo "=== Claude Code Traffic Light 构建脚本 ==="

# ── 1. 准备 Python 虚拟环境 ──
# 隔离项目依赖，避免与系统 Python 冲突
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# ── 2. 安装运行依赖 ──
# rumps（菜单栏）、PyInstaller 等，见 requirements.txt
echo "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 3. 清理上次构建产物 ──
# build/、dist/ 为 PyInstaller 中间目录；*.spec 为自动生成的打包配置（无需保留）
echo "清理旧构建..."
rm -rf build dist *.spec

# ── 4. PyInstaller 打包 ──
# --windowed：不显示终端窗口（菜单栏应用）
# --icon：应用图标，使用 assets/icon.icns
# 入口为 main.py，内部会加载 core/macos 菜单栏逻辑
echo "打包中..."
pyinstaller \
    --name "ClaudeTrafficLight" \
    --windowed \
    --noconfirm \
    --clean \
    --icon "assets/icon.icns" \
    main.py

echo "=== 构建完成 ==="
echo "应用位置: dist/ClaudeTrafficLight.app"
