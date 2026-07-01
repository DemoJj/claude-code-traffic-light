# Claude Code Traffic Light

Claude Code 菜单栏状态监控工具 —— 通过红绿灯直观显示 Claude Code 会话状态。

![macOS](https://img.shields.io/badge/macOS-supported-blue)
![Windows](https://img.shields.io/badge/Windows-supported-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 功能特性

- **红绿灯状态指示**：在 macOS 菜单栏 / Windows 系统托盘实时显示 Claude Code 会话状态
  - 🟢 绿灯常亮 — 会话进行中
  - 🟡 黄灯闪烁 — 需要确认（等待权限）
  - 🔴 红灯常亮 — 会话结束
- **Windows 浮窗模式**：右键菜单可切换为置顶浮窗，**同时监控所有活跃项目**（每行一个项目 + 独立红绿灯），支持 30%~100% 透明度，可拖拽定位
- **多项目支持**：同时监控多个项目的 Claude Code 状态，一键切换
- **自动配置**：启动时自动配置 Claude Code hooks，退出时自动还原
- **配置备份**：安全备份原始 `settings.json`，确保不影响现有配置

## 安装

### 方式一：下载预编译应用（推荐）

前往 [Releases](https://github.com/DemoJj/claude-code-traffic-light/releases) 页面下载最新版本：

**macOS**

- **ClaudeTrafficLight.app.zip** — 直接解压使用
- **ClaudeTrafficLight-x.x.x.dmg** — 安装包

下载后将应用拖入 Applications 文件夹，双击启动即可。

**Windows**

- **ClaudeTrafficLight.exe** — 单文件可执行程序（与 macOS 包一同发布于 [Releases](https://github.com/DemoJj/claude-code-traffic-light/releases)），下载后双击运行即可

首次运行若出现 SmartScreen 提示，选择「仍要运行」；程序会出现在系统托盘（任务栏右下角）。

### 方式二：从源码构建

```bash
# 克隆项目
git clone https://github.com/DemoJj/claude-code-traffic-light.git
cd claude-code-traffic-light

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### macOS 构建

```bash
bash build.sh
```

构建完成后，应用位于 `dist/ClaudeTrafficLight.app`。

#### Windows 构建

```bash
python build_windows.py
```

构建完成后，可执行文件位于 `dist/ClaudeTrafficLight.exe`。

### 方式三：直接运行 Python 脚本

```bash
# macOS / Linux
python3 main.py

# Windows
python main.py
# 或
python -m core
```

- **macOS**：启动后菜单栏会出现红绿灯图标
- **Windows**：启动后系统托盘（任务栏右下角）会出现红绿灯图标

自动开始监控 Claude Code 状态。

#### Windows 浮窗模式

右键托盘图标 → **显示样式** → **浮窗**，即可切换为置顶浮窗：

- 拖拽浮窗可调整位置（位置会自动保存，且不会拖出屏幕外）
- **右键浮窗** 可打开与托盘相同的菜单（项目切换、显示样式、透明度等）
- **透明度** 子菜单可选 30% / 50% / 70% / 85% / 100%
- 托盘图标仍保留，用于右键菜单操作

### 退出

- **macOS**：点击菜单栏红绿灯图标，选择「退出」
- **Windows**：右键托盘图标，选择「退出」
- 或按 `Ctrl+C` 终止进程（控制台模式）

退出时会自动还原 Claude Code 的 `settings.json` 配置。

## 工作原理

1. **Hook 机制**：通过 Claude Code 的 hooks 功能，在会话状态变化时写入状态文件
2. **状态轮询**：定时读取状态文件，更新菜单栏显示
3. **闪烁效果**：黄灯状态通过定时器实现闪烁效果

### Hook 事件映射

| 事件 | 状态 |
|------|------|
| `SessionStart` | 红灯（会话开始） |
| `UserPromptSubmit` | 绿灯（用户输入） |
| `PreToolUse` (需权限工具) | 黄灯（等待确认） |
| `PostToolUse` (需权限工具) | 绿灯（工具执行完成） |
| `Stop` | 红灯（会话结束） |

## 配置说明

应用会自动配置以下路径：

- 状态文件：`~/.claude/traffic_light/*.state`
- 配置备份：`~/.claude/traffic_light/settings_backup.json`
- UI 偏好（显示样式/透明度/浮窗位置）：`~/.claude/traffic_light/ui_prefs.json`
- 项目选择：`~/.claude/traffic_light/selected_project`

## 系统要求

- **macOS** 10.15+
- **Windows** 10+
- Python 3.9+（仅从源码运行/构建时需要）
- Windows 需已安装 Git Bash（Claude Code hook 运行环境，通常随 Git for Windows 安装）

## 发布流程

### 自动发布（推荐）

1. 提交更改并打 tag（版本号即 tag 名）：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. GitHub Actions 会自动构建并发布到 Releases

### 手动发布

1. 在 GitHub Actions 页面手动触发 `Build and Release` 工作流
2. 输入版本号即可

## 开发与测试

### 项目结构

```
main.py              # 入口
core/                # 业务逻辑（配置、项目、hooks、状态轮询）
  rendering/         # 图标与浮窗绘制
  windows/           # Windows 托盘与浮窗
  macos/             # macOS 菜单栏
tests/               # 单元测试
build_windows.py     # Windows 打包
build.sh             # macOS 打包
```

### 运行测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

测试覆盖 `core/` 中的核心业务逻辑：项目名显示、可见项目同步、托盘状态聚合、UI 偏好读写、Hook 合并、状态轮询等。GUI 相关模块（tkinter 浮窗、系统托盘）未纳入单元测试。

Push 或 PR 到 `main`/`master` 分支时，GitHub Actions 会自动运行测试（`.github/workflows/test.yml`）。

## 贡献

欢迎提交 Issue 和 Pull Request！请参考以下规范：

- **Issue**：使用 Issue 模板提交 Bug 报告或功能建议
- **PR**：使用 PR 模板描述变更内容，提交前请本地运行 `python -m pytest tests/ -v` 确保通过

## License

MIT License
