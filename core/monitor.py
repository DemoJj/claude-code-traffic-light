"""状态轮询与 Claude 配置读取（跨平台）"""
import json
import time
from pathlib import Path

from core.config import CONFIG_PATH, MENU_REFRESH_INTERVAL
from core.projects import (
    aggregate_tray_state,
    get_selected_project,
    get_tray_aggregate_projects,
    get_tray_project,
    list_active_projects,
    set_selected_project,
    sync_visible_projects,
)


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

    def check_state(self, ui_prefs=None):
        """读取状态文件并更新状态"""
        changed = False
        menu_needs_refresh = False

        if ui_prefs is not None:
            old_visible = list(ui_prefs.get("visible_projects", []))
            sync_visible_projects(ui_prefs)
            if ui_prefs.get("visible_projects") != old_visible:
                menu_needs_refresh = True
            tray_project = get_tray_project(ui_prefs)
            if tray_project != self.selected_project:
                self.selected_project = tray_project
                set_selected_project(tray_project)
                changed = True

        try:
            projects_for_tray = get_tray_aggregate_projects(ui_prefs)
            content = aggregate_tray_state(projects_for_tray)
            if content != self.state:
                self._set_state(content)
                changed = True
        except Exception:
            pass

        now = time.time()
        if now - self.last_menu_build_time > MENU_REFRESH_INTERVAL:
            projects = list_active_projects()
            if ui_prefs is not None:
                old_visible = list(ui_prefs.get("visible_projects", []))
                sync_visible_projects(ui_prefs)
                if ui_prefs.get("visible_projects") != old_visible:
                    menu_needs_refresh = True
                tray_project = get_tray_project(ui_prefs)
                if tray_project != self.selected_project:
                    self.selected_project = tray_project
                    set_selected_project(tray_project)
                    changed = True
            elif projects and self.selected_project not in projects:
                self.selected_project = projects[0]
                set_selected_project(self.selected_project)
                changed = True
            if projects != self.last_projects:
                self.last_projects = projects
                menu_needs_refresh = True
                changed = True
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
