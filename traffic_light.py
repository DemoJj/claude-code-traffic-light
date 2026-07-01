#!/usr/bin/env python3
"""
Claude Code 红绿灯状态监视器
三个灯同时显示，根据状态变化：
- 绿灯常亮：会话进行中
- 黄灯闪烁：需要确认（等待权限）
- 红灯常亮：会话结束

macOS：菜单栏 (rumps)  |  Windows：系统托盘 (pystray)
"""
import atexit
import json
import os
import shutil
import signal
import sys
import threading
import time
from pathlib import Path

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# ---------- 配置 ----------
BASE_DIR = str(Path.home() / ".claude" / "traffic_light")
STATE_DIR = BASE_DIR
CONFIG_PATH = str(Path.home() / ".claude" / "settings.json")
BACKUP_PATH = os.path.join(BASE_DIR, "settings_backup.json")
SELECTED_FILE = os.path.join(BASE_DIR, "selected_project")
# Claude Code 在 Windows 上也通过 Git Bash 执行 hook，路径必须用 POSIX 格式
HOOK_STATE_DIR = "~/.claude/traffic_light"
POLL_INTERVAL = 0.3
BLINK_INTERVAL = 0.5
MENU_REFRESH_INTERVAL = 2

TRAFFIC_MARKER = "traffic_light_app"

LIGHT_ON = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
LIGHT_OFF = "⚫"

# 托盘图标颜色 (R, G, B)
LIGHT_COLORS = {
    "red": (220, 50, 50),
    "yellow": (255, 200, 0),
    "green": (50, 200, 80),
}
LIGHT_DIM = (50, 50, 50)
HOUSING_COLOR = (30, 30, 30)


def get_state_file(project_name=None):
    """获取指定项目的状态文件路径"""
    if project_name is None:
        project_name = get_selected_project()
    return os.path.join(STATE_DIR, f"{project_name}.state")


def get_selected_project():
    """获取当前选中的项目名，默认选中第一个活跃项目"""
    try:
        if Path(SELECTED_FILE).exists():
            return Path(SELECTED_FILE).read_text(encoding="utf-8").strip()
    except Exception:
        pass
    projects = list_active_projects()
    return projects[0] if projects else "default"


def set_selected_project(project_name):
    """设置当前选中的项目"""
    try:
        Path(SELECTED_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(SELECTED_FILE).write_text(project_name, encoding="utf-8")
    except Exception:
        pass


def list_active_projects():
    """列出所有有状态文件的项目"""
    try:
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
        return sorted(f.stem for f in Path(STATE_DIR).glob("*.state"))
    except Exception:
        return []


def backup_config():
    """备份原始配置文件"""
    if Path(CONFIG_PATH).exists():
        try:
            shutil.copy2(CONFIG_PATH, BACKUP_PATH)
            print(f"已备份原始配置: {BACKUP_PATH}")
            return True
        except Exception as e:
            print(f"备份配置失败: {e}")
    return True


_restored = False


def restore_config():
    """还原备份的配置文件并清理所有新增文件"""
    global _restored
    if _restored:
        return
    _restored = True

    if Path(BACKUP_PATH).exists():
        try:
            shutil.copy2(BACKUP_PATH, CONFIG_PATH)
            Path(BACKUP_PATH).unlink()
            print(f"已还原原始配置: {CONFIG_PATH}")
        except Exception as e:
            print(f"还原配置失败: {e}")

    if Path(STATE_DIR).exists():
        try:
            shutil.rmtree(STATE_DIR)
            print(f"已清理状态目录: {STATE_DIR}")
        except Exception as e:
            print(f"清理状态目录失败: {e}")

    if Path(SELECTED_FILE).exists():
        try:
            Path(SELECTED_FILE).unlink()
            print(f"已清理选择文件: {SELECTED_FILE}")
        except Exception as e:
            print(f"清理选择文件失败: {e}")

    old_file = os.path.expanduser("~/.claude/.traffic_light")
    if Path(old_file).exists():
        try:
            Path(old_file).unlink()
            print(f"已清理旧版状态文件: {old_file}")
        except Exception:
            pass


def _is_traffic_hook(entry):
    """判断一个 hook 条目是否属于红绿灯"""
    for hook in entry.get("hooks", []):
        cmd = hook.get("command", "")
        if TRAFFIC_MARKER in cmd or HOOK_STATE_DIR in cmd:
            return True
    return False


def _make_hook_entry(command, matcher=""):
    """创建一个符合 Claude Code 格式的 hook 条目"""
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": command}],
    }


def _hook_cmd(state):
    """生成 hook 命令（Claude Code 在 macOS/Windows 上均通过 bash 执行）"""
    marker = f"# {TRAFFIC_MARKER}"
    return (
        f'project=$(basename "${{CLAUDE_PROJECT_DIR:-$PWD}}") && '
        f'mkdir -p {HOOK_STATE_DIR} && echo {state} > {HOOK_STATE_DIR}/"$project".state {marker}'
    )


def configure_hooks():
    """安全地将所需的 hook 合并到 ~/.claude/settings.json"""
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(STATE_DIR).mkdir(parents=True, exist_ok=True)

    backup_config()

    config = {}
    if Path(CONFIG_PATH).exists():
        try:
            config = json.loads(Path(CONFIG_PATH).read_text(encoding="utf-8"))
        except Exception:
            config = {}

    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}

    hook_cmd = _hook_cmd
    permission_tools = "Bash|Write|Edit|NotebookEdit|WebFetch"

    desired = {
        "SessionStart": [_make_hook_entry(hook_cmd("red"))],
        "UserPromptSubmit": [_make_hook_entry(hook_cmd("green"))],
        "PermissionRequest": [_make_hook_entry(hook_cmd("yellow"))],
        "PreToolUse": [_make_hook_entry(hook_cmd("yellow"), matcher=permission_tools)],
        "PostToolUse": [_make_hook_entry(hook_cmd("green"), matcher=permission_tools)],
        "Stop": [_make_hook_entry(hook_cmd("red"))],
        "SessionEnd": [_make_hook_entry(hook_cmd("red"))],
    }

    for hook_name, new_entries in desired.items():
        existing = hooks.get(hook_name, [])
        if not isinstance(existing, list):
            existing = []
        cleaned = [entry for entry in existing if not _is_traffic_hook(entry)]
        cleaned.extend(new_entries)
        hooks[hook_name] = cleaned
        print(f"已设置 hook: {hook_name}")

    config["hooks"] = hooks
    try:
        Path(CONFIG_PATH).write_text(
            json.dumps(config, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Claude Code 配置已更新: {CONFIG_PATH}")
    except Exception as e:
        print(f"写入配置失败: {e}")


def load_claude_info():
    """读取 Claude 配置信息"""
    info = {"model": "未知"}
    try:
        if Path(CONFIG_PATH).exists():
            config = json.loads(Path(CONFIG_PATH).read_text(encoding="utf-8"))
            model = config.get("env", {}).get("ANTHROPIC_MODEL", "") or config.get("model", "未知")
            info["model"] = model
    except Exception:
        pass
    return info


class StateMonitor:
    """共享的状态轮询逻辑"""

    def __init__(self):
        self.state = "red"
        self.blink_on = True
        self.selected_project = get_selected_project()
        self.last_projects = []
        self.last_menu_build_time = 0
        self.claude_info = load_claude_info()
        self._on_state_change = None

    def set_on_state_change(self, callback):
        self._on_state_change = callback

    def select_project(self, project_name):
        self.selected_project = project_name.strip()
        set_selected_project(self.selected_project)
        self._set_state("red")

    def check_state(self):
        """读取状态文件并更新状态"""
        state_file = get_state_file(self.selected_project)
        changed = False
        try:
            if Path(state_file).exists():
                content = Path(state_file).read_text(encoding="utf-8").strip().lower()
                if content in ("green", "yellow", "red") and self.state != content:
                    self._set_state(content)
                    changed = True
            elif self.state != "red":
                self._set_state("red")
                changed = True
        except Exception:
            pass

        now = time.time()
        menu_needs_refresh = False
        if now - self.last_menu_build_time > MENU_REFRESH_INTERVAL:
            projects = list_active_projects()
            if projects and self.selected_project not in projects:
                self.selected_project = projects[0]
                set_selected_project(self.selected_project)
                changed = True
            if projects != self.last_projects:
                self.last_projects = projects
                menu_needs_refresh = True
            self.last_menu_build_time = now

        return changed, menu_needs_refresh

    def _set_state(self, new_state):
        self.state = new_state
        self.blink_on = True
        if self._on_state_change:
            self._on_state_change()

    def toggle_blink(self):
        self.blink_on = not self.blink_on
        if self._on_state_change:
            self._on_state_change()


def render_traffic_icon(state, blink_on):
    """绘制托盘/图标用红绿灯图像"""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    housing = (18, 8, 46, 56)
    draw.rounded_rectangle(housing, radius=8, fill=HOUSING_COLOR)

    cx = 32
    positions = [("red", 20), ("yellow", 32), ("green", 44)]
    for color_name, cy in positions:
        if state == color_name:
            if color_name == "yellow" and not blink_on:
                fill = LIGHT_DIM
            else:
                fill = LIGHT_COLORS[color_name]
        else:
            fill = LIGHT_DIM
        draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=fill)

    return img


def format_title(state, blink_on):
    """macOS 菜单栏文字显示"""
    lights = [LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
    if state == "green":
        lights[2] = LIGHT_ON["green"]
    elif state == "yellow":
        lights[1] = LIGHT_ON["yellow"] if blink_on else LIGHT_OFF
    else:
        lights[0] = LIGHT_ON["red"]
    return " ".join(lights)


# ---------- Windows 系统托盘 ----------
class WindowsTrayApp:
    def __init__(self):
        import pystray

        self.pystray = pystray
        self.monitor = StateMonitor()
        self.monitor.set_on_state_change(self.update_display)
        self._stop = threading.Event()
        self.icon = pystray.Icon(
            "Claude Traffic Light",
            render_traffic_icon(self.monitor.state, self.monitor.blink_on),
            "Claude Code 红绿灯",
            menu=self._build_menu(),
        )

    def _project_action(self, project):
        def action(_icon, _item):
            self._on_select_project(project)
        return action

    def _project_checked(self, project):
        def checked(_item):
            return project == self.monitor.selected_project
        return checked

    def _build_menu(self):
        projects = list_active_projects()
        self.monitor.last_projects = projects

        if projects:
            project_items = [
                self.pystray.MenuItem(
                    project,
                    self._project_action(project),
                    checked=self._project_checked(project),
                    radio=True,
                )
                for project in projects
            ]
        else:
            project_items = [self.pystray.MenuItem("(无活跃项目)", None, enabled=False)]

        return self.pystray.Menu(
            self.pystray.MenuItem("选择项目", self.pystray.Menu(*project_items)),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem(f"当前项目: {self.monitor.selected_project}", None, enabled=False),
            self.pystray.MenuItem(f"模型: {self.monitor.claude_info['model']}", None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem("🟢 绿灯 - 会话进行中", None, enabled=False),
            self.pystray.MenuItem("🟡 黄灯 - 需要确认", None, enabled=False),
            self.pystray.MenuItem("🔴 红灯 - 会话结束", None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem("退出", self._quit),
        )

    def _on_select_project(self, project_name):
        self.monitor.select_project(project_name)
        self.icon.menu = self._build_menu()
        self.update_display()

    def _quit(self, _icon, _item):
        self._stop.set()
        self.icon.stop()

    def update_display(self):
        self.icon.icon = render_traffic_icon(self.monitor.state, self.monitor.blink_on)
        status = {"green": "进行中", "yellow": "等待确认", "red": "已结束"}
        self.icon.title = f"Claude Code - {status.get(self.monitor.state, '')}"

    def _setup(self, icon):
        icon.visible = True
        self.monitor.check_state()
        self.update_display()
        last_blink = time.time()
        while not self._stop.is_set():
            changed, menu_refresh = self.monitor.check_state()
            now = time.time()
            if now - last_blink >= BLINK_INTERVAL:
                self.monitor.toggle_blink()
                last_blink = now
            elif changed:
                self.update_display()
            if menu_refresh:
                self.icon.menu = self._build_menu()
                self.icon.update_menu()
            time.sleep(POLL_INTERVAL)

    def run(self):
        self.icon.run(setup=self._setup)


# ---------- macOS 菜单栏 ----------
def _create_macos_app():
    import rumps

    class TrafficLightApp(rumps.App):
        def __init__(self):
            super().__init__("", quit_button="退出")
            self.monitor = StateMonitor()
            self.monitor.set_on_state_change(self.update_display)

            rumps.Timer(self._on_poll, POLL_INTERVAL).start()
            rumps.Timer(self._on_blink, BLINK_INTERVAL).start()

            self._build_menu()
            self.update_display()

        def _build_menu(self):
            self.menu.clear()

            project_menu = rumps.MenuItem("📁 选择项目")
            projects = list_active_projects()
            if not projects:
                item = rumps.MenuItem("  (无活跃项目)")
                item.set_callback(None)
                project_menu.add(item)
            else:
                for project in projects:
                    item = rumps.MenuItem(f"  {project}")
                    item.set_callback(self._on_select_project)
                    if project == self.monitor.selected_project:
                        item.state = True
                    project_menu.add(item)
            self.menu.add(project_menu)

            self.menu.add(rumps.separator)
            self.menu.add(rumps.MenuItem("📊 当前项目", callback=None))
            self.menu.add(rumps.MenuItem(f"  项目: {self.monitor.selected_project}"))
            self.menu.add(rumps.MenuItem(f"  模型: {self.monitor.claude_info['model']}"))

            self.menu.add(rumps.separator)
            self.menu.add(rumps.MenuItem("状态说明", callback=None))
            self.menu.add(rumps.MenuItem("🟢 绿灯常亮 - 会话进行中"))
            self.menu.add(rumps.MenuItem("🟡 黄灯闪烁 - 需要确认"))
            self.menu.add(rumps.MenuItem("🔴 红灯常亮 - 会话结束"))

            self.monitor.last_projects = projects
            self.monitor.last_menu_build_time = time.time()

        def _on_select_project(self, sender):
            self.monitor.select_project(sender.title.strip())
            self._build_menu()
            self.update_display()

        def _on_poll(self, _):
            _, menu_refresh = self.monitor.check_state()
            if menu_refresh:
                self._build_menu()

        def _on_blink(self, _):
            self.monitor.toggle_blink()
            self.update_display()

        def update_display(self):
            self.title = format_title(self.monitor.state, self.monitor.blink_on)

    return TrafficLightApp


# ---------- 入口 ----------
def main():
    if not IS_WINDOWS and not IS_MACOS:
        print("当前仅支持 Windows 和 macOS")
        sys.exit(1)

    print("正在配置 Claude Code hooks...")
    configure_hooks()

    atexit.register(restore_config)

    def signal_handler(_sig, _frame):
        restore_config()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    print("启动红绿灯监视器...")
    if IS_WINDOWS:
        WindowsTrayApp().run()
    else:
        _create_macos_app().run()


if __name__ == "__main__":
    main()
