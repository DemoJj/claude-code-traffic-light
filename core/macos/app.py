"""macOS 菜单栏应用（rumps）"""
from core.config import BLINK_INTERVAL, POLL_INTERVAL
from core.monitor import StateMonitor
from core.projects import (
    display_project_name,
    list_active_projects,
    menu_project_label,
)
from core.rendering.icon import format_title


def create_macos_app():
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

            project_menu = rumps.MenuItem("📁 显示项目")
            projects = list_active_projects()
            if not projects:
                item = rumps.MenuItem("  (无活跃项目)")
                item.set_callback(None)
                project_menu.add(item)
            else:
                for project in projects:
                    item = rumps.MenuItem(f"  {menu_project_label(project)}")
                    item.set_callback(lambda _sender, p=project: self._on_select_project_id(p))
                    if project == self.monitor.selected_project:
                        item.state = True
                    project_menu.add(item)
            self.menu.add(project_menu)

            self.menu.add(rumps.separator)
            self.menu.add(rumps.MenuItem("📊 当前项目", callback=None))
            self.menu.add(rumps.MenuItem(f"  项目: {display_project_name(self.monitor.selected_project)}"))
            self.menu.add(rumps.MenuItem(f"  模型: {self.monitor.claude_info['model']}"))

            self.menu.add(rumps.separator)
            self.menu.add(rumps.MenuItem("状态说明", callback=None))
            self.menu.add(rumps.MenuItem("🟢 绿灯常亮 - 会话进行中"))
            self.menu.add(rumps.MenuItem("🟡 黄灯闪烁 - 需要确认"))
            self.menu.add(rumps.MenuItem("🔴 红灯常亮 - 会话结束"))

            self.monitor.last_projects = projects
            self.monitor.last_menu_build_time = __import__("time").time()

        def _on_select_project_id(self, project_id):
            self.monitor.select_project(project_id)
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
