"""Windows 系统托盘应用（pystray + 可选浮窗）"""
import threading
import time

from core.config import (
    BLINK_INTERVAL,
    DISPLAY_FLOAT,
    DISPLAY_TRAY,
    FLOAT_THEME_PRESETS,
    OPACITY_PRESETS,
    POLL_INTERVAL,
    THEME_DARK,
    THEME_LIGHT,
    normalize_theme,
)
from core.monitor import StateMonitor
from core.prefs import load_ui_prefs, save_ui_prefs
from core.projects import (
    aggregate_tray_state,
    build_float_project_rows,
    get_tray_aggregate_projects,
    get_tray_project,
    list_active_projects,
    menu_project_label,
    set_selected_project,
    sync_visible_projects,
)
from core.rendering.icon import render_traffic_icon
from core.windows.float_window import FloatWindow
from core.windows.tray_icon import WM_SHOW_FLOAT_MENU, create_traffic_light_icon_class


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
        self._float_menu_pos = (0, 0)
        sync_visible_projects(self.ui_prefs)
        self.monitor.selected_project = get_tray_project(self.ui_prefs)
        set_selected_project(self.monitor.selected_project)
        icon_class = create_traffic_light_icon_class(pystray)
        self.icon = icon_class(
            "Claude Traffic Light",
            render_traffic_icon(self.monitor.state, self.monitor.blink_on),
            "Claude Code 红绿灯",
            menu=self._build_menu(),
            tray_app=self,
        )

    def _ensure_float_window(self):
        if self.float_window is None:
            self.float_window = FloatWindow(self.ui_prefs, self)
        return self.float_window

    def _refresh_menus(self):
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    def show_native_context_menu(self, x, y):
        """浮窗右键复用托盘原生 Windows 菜单（通过 pystray 消息线程弹出）"""
        from pystray._util import win32 as pystray_win32

        hwnd = getattr(self.icon, "_hwnd", None)
        if not hwnd:
            return

        self._float_menu_pos = (int(x), int(y))
        pystray_win32.PostMessage(hwnd, WM_SHOW_FLOAT_MENU, 0, 0)

    def _project_visibility_action(self, project):
        def action(_icon, _item):
            visible = project in self.ui_prefs.get("visible_projects", [])
            self._set_project_visible(project, not visible)
        return action

    def _project_visibility_checked(self, project):
        def checked(_item):
            return project in self.ui_prefs.get("visible_projects", [])
        return checked

    def _project_visibility_enabled(self, project):
        def enabled(_item):
            visible = self.ui_prefs.get("visible_projects", [])
            return not (project in visible and len(visible) <= 1)

        return enabled

    def _set_project_visible(self, project, visible):
        projects_list = list(self.ui_prefs.get("visible_projects", []))
        if visible:
            if project not in projects_list:
                projects_list.append(project)
        elif project in projects_list:
            if len(projects_list) <= 1:
                return
            projects_list.remove(project)
        self.ui_prefs["visible_projects"] = projects_list
        save_ui_prefs(self.ui_prefs)
        self._update_tray_from_visible()
        self._refresh_menus()
        self.update_display()

    def _update_tray_from_visible(self):
        tray_project = get_tray_project(self.ui_prefs)
        if tray_project != self.monitor.selected_project:
            self.monitor.selected_project = tray_project
            set_selected_project(tray_project)
        content = aggregate_tray_state(get_tray_aggregate_projects(self.ui_prefs))
        self.monitor._set_state(content)

    def _theme_action(self, theme):
        def action(_icon, _item):
            self._set_theme(theme)
        return action

    def _theme_checked(self, theme):
        def checked(_item):
            return normalize_theme(self.ui_prefs) == theme
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

    def _set_display_mode(self, mode):
        self.ui_prefs["display_mode"] = mode
        save_ui_prefs(self.ui_prefs)
        self._apply_display_mode()
        self.update_display()
        self._refresh_menus()

    def _set_opacity(self, opacity):
        self.ui_prefs["opacity"] = float(opacity)
        save_ui_prefs(self.ui_prefs)
        self.update_display()
        self._refresh_menus()

    def _set_theme(self, theme):
        if theme not in FLOAT_THEME_PRESETS:
            theme = THEME_DARK
        self.ui_prefs["theme"] = theme
        save_ui_prefs(self.ui_prefs)
        self.update_display()
        self._refresh_menus()

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
        sync_visible_projects(self.ui_prefs)

        if projects:
            project_items = [
                self.pystray.MenuItem(
                    menu_project_label(project),
                    self._project_visibility_action(project),
                    checked=self._project_visibility_checked(project),
                    enabled=self._project_visibility_enabled(project),
                )
                for project in projects
            ]
        else:
            project_items = [self.pystray.MenuItem("(无活跃项目)", None, enabled=False)]

        return self.pystray.Menu(
            self.pystray.MenuItem("显示项目", self.pystray.Menu(*project_items)),
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
                        "浮窗",
                        self._display_mode_action(DISPLAY_FLOAT),
                        checked=self._display_mode_checked(DISPLAY_FLOAT),
                        radio=True,
                    ),
                ),
            ),
            self.pystray.MenuItem(
                "主题",
                self.pystray.Menu(
                    self.pystray.MenuItem(
                        "黑夜模式",
                        self._theme_action(THEME_DARK),
                        checked=self._theme_checked(THEME_DARK),
                        radio=True,
                    ),
                    self.pystray.MenuItem(
                        "白天模式",
                        self._theme_action(THEME_LIGHT),
                        checked=self._theme_checked(THEME_LIGHT),
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
            self.pystray.MenuItem("绿灯 - 会话进行中", None, enabled=False),
            self.pystray.MenuItem("黄灯 - 需要确认", None, enabled=False),
            self.pystray.MenuItem("红灯 - 会话结束", None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem("退出", self._quit),
        )

    def _update_float_display(self):
        fw = self._ensure_float_window()
        rows = build_float_project_rows(self.ui_prefs)
        fw._update_impl(
            rows,
            self.monitor.blink_on,
            self.ui_prefs.get("opacity", 0.85),
        )

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
        self.icon.icon = render_traffic_icon(state, blink_on)
        status = {"green": "进行中", "yellow": "等待确认", "red": "已结束"}
        self.icon.title = f"Claude Code - {status.get(state, '')}"
        if self.ui_prefs.get("display_mode") == DISPLAY_FLOAT and self._tk_root is not None:
            self._tk_root.after(0, self._update_float_display)

    def _setup(self, icon):
        self._show_tray_icon(icon)
        self._apply_display_mode()
        self.monitor.check_state(self.ui_prefs)
        self.update_display()
        print("托盘图标已就绪，请查看任务栏右下角（可能被折叠在 ^ 图标内）", flush=True)
        last_blink = time.time()
        while not self._stop.is_set():
            changed, menu_refresh = self.monitor.check_state(self.ui_prefs)
            now = time.time()
            if now - last_blink >= BLINK_INTERVAL:
                self.monitor.toggle_blink()
                last_blink = now
            elif changed:
                self.update_display()
            if menu_refresh:
                self._refresh_menus()
                self.update_display()
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
