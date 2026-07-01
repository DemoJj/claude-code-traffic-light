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
UI_PREFS_FILE = str(Path.home() / ".claude" / "traffic_light_ui.json")
UI_PREFS_FILE_LEGACY = os.path.join(BASE_DIR, "ui_prefs.json")
# Claude Code 在 Windows 上也通过 Git Bash 执行 hook，路径必须用 POSIX 格式
HOOK_STATE_DIR = "~/.claude/traffic_light"
POLL_INTERVAL = 0.3
BLINK_INTERVAL = 0.5
MENU_REFRESH_INTERVAL = 2

DISPLAY_TRAY = "tray"
DISPLAY_FLOAT = "float"
OPACITY_PRESETS = [0.3, 0.5, 0.7, 0.85, 1.0]
DEFAULT_UI_PREFS = {
    "display_mode": DISPLAY_TRAY,
    "opacity": 0.85,
    "float_x": None,
    "float_y": None,
}

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
FLOAT_TRANSPARENT = "#010102"
FLOAT_BG = "#2b2b2b"
FLOAT_BORDER = "#454545"
FLOAT_TEXT_COLOR = "#e8e8e8"
FLOAT_SEPARATOR = "#454545"
FLOAT_LIGHT_RADIUS = 6
FLOAT_INNER_PAD = 10
FLOAT_NAME_MAX = 118
FLOAT_LIGHTS_SPACING = 10
FLOAT_LIGHT_DIAMETER = FLOAT_LIGHT_RADIUS * 2
FLOAT_LIGHTS_BLOCK = FLOAT_LIGHT_DIAMETER * 3 + FLOAT_LIGHTS_SPACING * 2
FLOAT_GAP = 8
FLOAT_WIDTH = (
    FLOAT_INNER_PAD + FLOAT_NAME_MAX + FLOAT_GAP + 1 + FLOAT_GAP + FLOAT_LIGHTS_BLOCK + FLOAT_INNER_PAD
)
FLOAT_HEIGHT = 34
FLOAT_RADIUS = 12
FLOAT_FONT = ("Segoe UI", 11)
FLOAT_SCALE = 3
FLOAT_BG_RGB = (43, 43, 43)
FLOAT_BORDER_RGB = (69, 69, 69)
FLOAT_TRANSPARENT_RGB = (1, 1, 2)
FLOAT_SEPARATOR_RGB = (69, 69, 69)
FLOAT_TEXT_RGB = (232, 232, 232)


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


def load_ui_prefs():
    """读取 UI 偏好（显示模式、透明度、浮窗位置）"""
    prefs = DEFAULT_UI_PREFS.copy()
    legacy = Path(UI_PREFS_FILE_LEGACY)
    current = Path(UI_PREFS_FILE)
    if not current.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, current)
        except Exception:
            pass
    try:
        if current.exists():
            saved = json.loads(current.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                prefs.update(saved)
    except Exception:
        pass
    if prefs.get("display_mode") not in (DISPLAY_TRAY, DISPLAY_FLOAT):
        prefs["display_mode"] = DISPLAY_TRAY
    try:
        prefs["opacity"] = float(prefs.get("opacity", 0.85))
    except (TypeError, ValueError):
        prefs["opacity"] = 0.85
    prefs["opacity"] = max(0.2, min(1.0, prefs["opacity"]))
    return prefs


def save_ui_prefs(prefs):
    """保存 UI 偏好"""
    try:
        Path(UI_PREFS_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(UI_PREFS_FILE).write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _rgb_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def truncate_project_name(name, max_width, font):
    """按像素宽度截断项目名称，超出部分用 ... 省略"""
    if not name:
        return "default"
    if font.measure(name) <= max_width:
        return name
    ellipsis = "..."
    if font.measure(ellipsis) > max_width:
        return ellipsis
    for end in range(len(name), 0, -1):
        candidate = name[:end] + ellipsis
        if font.measure(candidate) <= max_width:
            return candidate
    return ellipsis


def _light_fill(state, blink_on, color_name):
    if state == color_name:
        if color_name == "yellow" and not blink_on:
            return _rgb_hex(LIGHT_DIM)
        return _rgb_hex(LIGHT_COLORS[color_name])
    return _rgb_hex(LIGHT_DIM)


def _light_outline(state, blink_on, color_name):
    if state == color_name and (color_name != "yellow" or blink_on):
        r, g, b = LIGHT_COLORS[color_name]
        return f"#{min(r + 40, 255):02x}{min(g + 40, 255):02x}{min(b + 40, 255):02x}"
    return "#333333"


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _get_pil_font(size):
    from PIL import ImageFont

    for name in ("segoeui.ttf", "Segoe UI.ttf", "msyh.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _truncate_pil_text(text, font, max_width):
    if not text:
        return "default"
    if font.getlength(text) <= max_width:
        return text
    ellipsis = "..."
    for end in range(len(text), 0, -1):
        candidate = text[:end] + ellipsis
        if font.getlength(candidate) <= max_width:
            return candidate
    return ellipsis


def _get_monitor_work_area(x, y, width, height):
    """获取窗口所在显示器的可用工作区（不含任务栏）"""
    if not IS_WINDOWS:
        return 0, 0, width, height
    try:
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        point = wintypes.POINT(int(x + width // 2), int(y + height // 2))
        monitor = ctypes.windll.user32.MonitorFromPoint(point, 2)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            work = info.rcWork
            return work.left, work.top, work.right, work.bottom
    except Exception:
        pass
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        rect = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return 0, 0, 1920, 1040


def render_float_surface(state, blink_on, project_name, master=None):
    """用 PIL 超采样绘制浮窗，边缘更平滑"""
    from PIL import Image, ImageDraw, ImageTk

    scale = FLOAT_SCALE
    width = FLOAT_WIDTH * scale
    height = FLOAT_HEIGHT * scale
    img = Image.new("RGBA", (width, height), FLOAT_TRANSPARENT_RGB + (255,))
    draw = ImageDraw.Draw(img)

    radius = FLOAT_RADIUS * scale
    pad = FLOAT_INNER_PAD * scale
    name_max = FLOAT_NAME_MAX * scale
    font = _get_pil_font(FLOAT_FONT[1] * scale)

    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=radius,
        fill=FLOAT_BG_RGB + (255,),
        outline=FLOAT_BORDER_RGB + (255,),
        width=scale,
    )

    separator_x = pad + name_max + (FLOAT_GAP * scale) // 2
    draw.line(
        (separator_x, 7 * scale, separator_x, height - 7 * scale),
        fill=FLOAT_SEPARATOR_RGB + (255,),
        width=scale,
    )

    display_name = _truncate_pil_text(project_name, font, name_max - 4 * scale)
    draw.text((pad, height // 2), display_name, fill=FLOAT_TEXT_RGB + (255,), font=font, anchor="lm")

    lights_start = width - pad - FLOAT_LIGHTS_BLOCK * scale
    cy = height // 2
    light_r = FLOAT_LIGHT_RADIUS * scale
    for index, color_name in enumerate(["red", "yellow", "green"]):
        cx = lights_start + light_r + index * (FLOAT_LIGHT_DIAMETER + FLOAT_LIGHTS_SPACING) * scale
        fill_hex = _light_fill(state, blink_on, color_name)
        fill_rgb = _hex_to_rgb(fill_hex)
        outline_hex = _light_outline(state, blink_on, color_name)
        outline_rgb = _hex_to_rgb(outline_hex)
        active = state == color_name and (color_name != "yellow" or blink_on)
        if active:
            glow_r = light_r + scale
            glow = tuple(min(c + 30, 255) for c in fill_rgb)
            draw.ellipse(
                (cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r),
                fill=glow + (80,),
            )
        draw.ellipse(
            (cx - light_r, cy - light_r, cx + light_r, cy + light_r),
            fill=fill_rgb + (255,),
            outline=outline_rgb + (255,),
            width=(2 if active else 1) * scale,
        )

    img = img.resize((FLOAT_WIDTH, FLOAT_HEIGHT), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img, master=master)


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
        fill_hex = _light_fill(state, blink_on, color_name)
        r = int(fill_hex[1:3], 16)
        g = int(fill_hex[3:5], 16)
        b = int(fill_hex[5:7], 16)
        draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(r, g, b))

    return img


def save_tray_icon_ico(output_path):
    """生成与托盘一致的多尺寸 .ico，供 Windows exe 打包使用"""
    from PIL import Image

    base = render_traffic_icon("red", True).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [base.resize((size, size), Image.Resampling.LANCZOS) for size in sizes]
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(size, size) for size in sizes],
    )


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


class FloatWindow:
    """输入法风格的置顶浮窗，可拖拽、可调透明度（主线程 Toplevel）"""

    def __init__(self, prefs, app):
        self._app = app
        self._drag_offset = (0, 0)
        self._prefs = prefs
        self._visible = False
        self._project_name = ""
        self._state = "red"
        self._blink_on = True
        self._tk_image = None
        self.root = None
        self._label = None
        self._context_menu = None

    def _ensure_window(self):
        if self.root is not None:
            try:
                if self.root.winfo_exists():
                    return
            except Exception:
                pass
            self.root = None

        import tkinter as tk

        master = self._app._tk_root
        root = tk.Toplevel(master)
        self.root = root
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", FLOAT_TRANSPARENT)
        root.configure(bg=FLOAT_TRANSPARENT)
        root.geometry(f"{FLOAT_WIDTH}x{FLOAT_HEIGHT}")

        self._label = tk.Label(
            root,
            bg=FLOAT_TRANSPARENT,
            bd=0,
            highlightthickness=0,
        )
        self._label.pack(fill="both", expand=True)

        self._label.bind("<ButtonPress-1>", self._on_drag_start)
        self._label.bind("<B1-Motion>", self._on_drag_motion)
        self._label.bind("<ButtonRelease-1>", self._on_drag_end)
        self._label.bind("<Button-3>", self._on_right_click)

        self._app.attach_tk_menu_vars(master)
        self._apply_position()
        self._apply_opacity(self._prefs.get("opacity", 0.85))
        self._render_surface()

    def _dispatch(self, action, *args):
        master = self._app._tk_root
        if master is None:
            return
        master.after(0, lambda: self._execute(action, args))

    def _execute(self, action, args):
        try:
            if action is not self._destroy_impl:
                self._ensure_window()
            action(*args)
        except Exception as exc:
            print(f"浮窗操作失败: {exc}", flush=True)

    def is_ready(self):
        if self.root is None:
            return False
        try:
            return self.root.winfo_exists()
        except Exception:
            return False

    def _render_surface(self):
        if self._label is None:
            return
        self._tk_image = render_float_surface(
            self._state, self._blink_on, self._project_name, master=self.root
        )
        self._label.config(image=self._tk_image)

    def _clamp_position(self, x, y):
        if self.root is None:
            return int(x), int(y)
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), FLOAT_WIDTH)
        height = max(self.root.winfo_height(), FLOAT_HEIGHT)
        work_left, work_top, work_right, work_bottom = _get_monitor_work_area(x, y, width, height)
        x = max(work_left, min(int(x), work_right - width))
        y = max(work_top, min(int(y), work_bottom - height))
        return x, y

    def _apply_position(self):
        if self.root is None:
            return
        x = self._prefs.get("float_x")
        y = self._prefs.get("float_y")
        if x is None or y is None:
            x = self.root.winfo_screenwidth() - FLOAT_WIDTH - 24
            y = 80
        x, y = self._clamp_position(x, y)
        self.root.geometry(f"{FLOAT_WIDTH}x{FLOAT_HEIGHT}+{x}+{y}")

    def _apply_opacity(self, opacity):
        if self.root is None:
            return
        self.root.attributes("-alpha", opacity)

    def _on_drag_start(self, event):
        self._drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _on_drag_motion(self, event):
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        x, y = self._clamp_position(x, y)
        self.root.geometry(f"+{x}+{y}")

    def _on_drag_end(self, _event):
        x, y = self._clamp_position(self.root.winfo_x(), self.root.winfo_y())
        self.root.geometry(f"+{x}+{y}")
        self._prefs["float_x"] = x
        self._prefs["float_y"] = y
        save_ui_prefs(self._app.ui_prefs)

    def close_context_menu(self):
        menu = self._context_menu
        self._context_menu = None
        if menu is None:
            return
        try:
            menu.unpost()
        except Exception:
            pass
        try:
            menu.grab_release()
        except Exception:
            pass
        try:
            menu.destroy()
        except Exception:
            pass

    def _on_right_click(self, event):
        import tkinter as tk

        self.close_context_menu()
        self._app.sync_tk_menu_vars()
        menu = self._app.build_tk_context_menu(self.root)
        self._context_menu = menu

        def dismiss(_event=None):
            if self._context_menu is menu:
                self._context_menu = None
            try:
                menu.grab_release()
            except tk.TclError:
                pass
            try:
                menu.destroy()
            except tk.TclError:
                pass

        menu.bind("<Unmap>", dismiss, add="+")
        menu.bind("<Escape>", dismiss, add="+")
        menu.post(event.x_root, event.y_root)
        return "break"

    def _show_impl(self):
        self._apply_position()
        self.root.deiconify()
        self._visible = True

    def _hide_impl(self):
        self.root.withdraw()
        self._visible = False

    def _update_impl(self, state, blink_on, opacity, project_name):
        self._state = state
        self._blink_on = blink_on
        self._project_name = project_name
        self._render_surface()
        self._apply_opacity(opacity)

    def show(self):
        self._dispatch(self._show_impl)

    def hide(self):
        self._dispatch(self._hide_impl)

    def update(self, state, blink_on, opacity, project_name):
        self._dispatch(self._update_impl, state, blink_on, opacity, project_name)

    def destroy(self):
        self._dispatch(self._destroy_impl)

    def _destroy_impl(self):
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None


# ---------- Windows 系统托盘 ----------
class WindowsTrayApp:
    def __init__(self):
        import pystray

        self.pystray = pystray
        self.ui_prefs = load_ui_prefs()
        self.monitor = StateMonitor()
        self.monitor.set_on_state_change(self.update_display)
        self._stop = threading.Event()
        self.float_window = None
        self._tk_root = None
        self._tk_menu_root = None
        self._tk_project_var = None
        self._tk_mode_var = None
        self._tk_opacity_var = None
        self.icon = pystray.Icon(
            "Claude Traffic Light",
            render_traffic_icon(self.monitor.state, self.monitor.blink_on),
            "Claude Code 红绿灯",
            menu=self._build_menu(),
        )

    def _ensure_float_window(self):
        if self.float_window is None:
            self.float_window = FloatWindow(self.ui_prefs, self)
        return self.float_window

    def _refresh_menus(self):
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    def _project_action(self, project):
        def action(_icon, _item):
            self._on_select_project(project)
        return action

    def _project_checked(self, project):
        def checked(_item):
            return project == self.monitor.selected_project
        return checked

    def _display_mode_action(self, mode):
        def action(_icon, _item):
            self._set_display_mode(mode)
        return action

    def _display_mode_checked(self, mode):
        def checked(_item):
            return self.ui_prefs.get("display_mode") == mode
        return checked

    def _opacity_action(self, opacity):
        def action(_icon, _item):
            self._set_opacity(opacity)
        return action

    def _opacity_checked(self, opacity):
        def checked(_item):
            return abs(self.ui_prefs.get("opacity", 0.85) - opacity) < 0.01
        return checked

    def _opacity_menu_value(self):
        current = float(self.ui_prefs.get("opacity", 0.85))
        for preset in OPACITY_PRESETS:
            if abs(current - preset) < 0.01:
                return str(preset)
        return str(current)

    def attach_tk_menu_vars(self, root):
        """绑定浮窗菜单变量到 tk 主窗口，确保单选状态与托盘菜单一致"""
        import tkinter as tk

        if self._tk_menu_root is not root:
            self._tk_menu_root = root
            self._tk_project_var = tk.StringVar(master=root)
            self._tk_mode_var = tk.StringVar(master=root)
            self._tk_opacity_var = tk.StringVar(master=root)
        self.sync_tk_menu_vars()

    def sync_tk_menu_vars(self):
        """将当前状态同步到浮窗菜单变量"""
        if self._tk_project_var is None:
            return
        self._tk_project_var.set(self.monitor.selected_project)
        self._tk_mode_var.set(self.ui_prefs.get("display_mode", DISPLAY_TRAY))
        self._tk_opacity_var.set(self._opacity_menu_value())

    def _set_display_mode(self, mode):
        self.ui_prefs["display_mode"] = mode
        save_ui_prefs(self.ui_prefs)
        self.sync_tk_menu_vars()
        self._apply_display_mode()
        self.update_display()
        self._refresh_menus()

    def _set_opacity(self, opacity):
        self.ui_prefs["opacity"] = float(opacity)
        save_ui_prefs(self.ui_prefs)
        self.sync_tk_menu_vars()
        self.update_display()
        self._refresh_menus()

    def _tk_menu_callback(self, callback):
        """菜单项回调：先关闭菜单，再延迟执行，避免菜单闪烁/无法关闭"""
        def wrapper():
            self._close_float_context_menu()
            if self._tk_root is not None:
                self._tk_root.after(50, callback)
            else:
                callback()
        return wrapper

    def _close_float_context_menu(self):
        if self.float_window is not None:
            self.float_window.close_context_menu()

    def build_tk_context_menu(self, parent):
        """构建浮窗右键菜单（与托盘菜单功能与选中状态一致）"""
        import tkinter as tk

        menu = tk.Menu(parent, tearoff=0)
        projects = list_active_projects()

        project_menu = tk.Menu(menu, tearoff=0)
        if projects:
            for project in projects:
                project_menu.add_radiobutton(
                    label=project,
                    variable=self._tk_project_var,
                    value=project,
                    command=self._tk_menu_callback(
                        lambda p=project: self._on_select_project(p)
                    ),
                )
        else:
            project_menu.add_command(label="(无活跃项目)", state="disabled")
        menu.add_cascade(label="选择项目", menu=project_menu)

        menu.add_separator()

        style_menu = tk.Menu(menu, tearoff=0)
        style_menu.add_radiobutton(
            label="系统托盘",
            variable=self._tk_mode_var,
            value=DISPLAY_TRAY,
            command=self._tk_menu_callback(lambda: self._set_display_mode(DISPLAY_TRAY)),
        )
        style_menu.add_radiobutton(
            label="输入法浮窗",
            variable=self._tk_mode_var,
            value=DISPLAY_FLOAT,
            command=self._tk_menu_callback(lambda: self._set_display_mode(DISPLAY_FLOAT)),
        )
        menu.add_cascade(label="显示样式", menu=style_menu)

        opacity_menu = tk.Menu(menu, tearoff=0)
        for value in OPACITY_PRESETS:
            opacity_menu.add_radiobutton(
                label=f"{int(value * 100)}%",
                variable=self._tk_opacity_var,
                value=str(value),
                command=self._tk_menu_callback(lambda v=value: self._set_opacity(v)),
            )
        menu.add_cascade(label="透明度", menu=opacity_menu)

        menu.add_separator()
        menu.add_command(
            label=f"当前项目: {self.monitor.selected_project}",
            state="disabled",
        )
        menu.add_command(
            label=f"模型: {self.monitor.claude_info['model']}",
            state="disabled",
        )
        menu.add_separator()
        menu.add_command(label="绿灯 - 会话进行中", state="disabled")
        menu.add_command(label="黄灯 - 需要确认", state="disabled")
        menu.add_command(label="红灯 - 会话结束", state="disabled")
        menu.add_separator()
        menu.add_command(label="退出", command=self._tk_menu_callback(self._quit_from_float))
        return menu

    def _apply_display_mode(self):
        if self._tk_root is None:
            return

        def apply_mode():
            if self.ui_prefs.get("display_mode") == DISPLAY_FLOAT:
                fw = self._ensure_float_window()
                fw._ensure_window()
                fw._show_impl()
            elif self.float_window is not None and self.float_window.is_ready():
                self.float_window._hide_impl()

        self._tk_root.after(0, apply_mode)

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
            self.pystray.MenuItem(
                "显示样式",
                self.pystray.Menu(
                    self.pystray.MenuItem(
                        "系统托盘",
                        self._display_mode_action(DISPLAY_TRAY),
                        checked=self._display_mode_checked(DISPLAY_TRAY),
                        radio=True,
                    ),
                    self.pystray.MenuItem(
                        "输入法浮窗",
                        self._display_mode_action(DISPLAY_FLOAT),
                        checked=self._display_mode_checked(DISPLAY_FLOAT),
                        radio=True,
                    ),
                ),
            ),
            self.pystray.MenuItem(
                "透明度",
                self.pystray.Menu(
                    *[
                        self.pystray.MenuItem(
                            f"{int(value * 100)}%",
                            self._opacity_action(value),
                            checked=self._opacity_checked(value),
                            radio=True,
                        )
                        for value in OPACITY_PRESETS
                    ]
                ),
            ),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem(f"当前项目: {self.monitor.selected_project}", None, enabled=False),
            self.pystray.MenuItem(f"模型: {self.monitor.claude_info['model']}", None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem("绿灯 - 会话进行中", None, enabled=False),
            self.pystray.MenuItem("黄灯 - 需要确认", None, enabled=False),
            self.pystray.MenuItem("红灯 - 会话结束", None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem("退出", self._quit),
        )

    def _on_select_project(self, project_name):
        self.monitor.select_project(project_name)
        self.sync_tk_menu_vars()
        self._refresh_menus()
        self.update_display()

    def _quit_from_float(self):
        self._stop.set()

        def shutdown():
            if self.float_window is not None:
                self.float_window._destroy_impl()
            if self._tk_root is not None:
                self._tk_root.quit()

        if self._tk_root is not None:
            self._tk_root.after(0, shutdown)
        self.icon.stop()

    def _quit(self, _icon, _item):
        self._quit_from_float()

    def _show_tray_icon(self, icon):
        """消息循环就绪后再显示托盘，避免 visible 标志提前置位导致图标不出现"""
        icon._visible = False
        icon.visible = True

    def update_display(self):
        state = self.monitor.state
        blink_on = self.monitor.blink_on
        opacity = self.ui_prefs.get("opacity", 0.85)
        self.icon.icon = render_traffic_icon(state, blink_on)
        status = {"green": "进行中", "yellow": "等待确认", "red": "已结束"}
        self.icon.title = f"Claude Code - {status.get(state, '')}"
        if self.ui_prefs.get("display_mode") == DISPLAY_FLOAT and self._tk_root is not None:
            self._tk_root.after(0, self._update_float_display)

    def _update_float_display(self):
        fw = self._ensure_float_window()
        fw._update_impl(
            self.monitor.state,
            self.monitor.blink_on,
            self.ui_prefs.get("opacity", 0.85),
            self.monitor.selected_project,
        )

    def _setup(self, icon):
        self._show_tray_icon(icon)
        self._apply_display_mode()
        self.monitor.check_state()
        self.update_display()
        print("托盘图标已就绪，请查看任务栏右下角（可能被折叠在 ^ 图标内）", flush=True)
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
                self._refresh_menus()
            time.sleep(POLL_INTERVAL)

    def run(self):
        import tkinter as tk

        self._tk_root = tk.Tk()
        self._tk_root.withdraw()
        self.icon.run_detached(setup=self._setup)
        if self.ui_prefs.get("display_mode") == DISPLAY_FLOAT:
            self._tk_root.after(0, self._apply_display_mode)
        try:
            self._tk_root.mainloop()
        finally:
            try:
                self._tk_root.destroy()
            except Exception:
                pass
            self._tk_root = None


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
