"""扩展 pystray 托盘图标，支持浮窗右键弹出同一菜单"""

WM_SHOW_FLOAT_MENU = 0x400 + 12  # WM_USER + 12，与 pystray 内部消息错开


def create_traffic_light_icon_class(pystray_module):
    """创建支持浮窗右键菜单的托盘图标类（菜单必须在 pystray 消息线程弹出）"""
    from pystray._util import win32 as pystray_win32

    class TrafficLightIcon(pystray_module.Icon):
        def __init__(self, *args, tray_app=None, **kwargs):
            super().__init__(*args, **kwargs)
            self._tray_app = tray_app
            self._message_handlers[WM_SHOW_FLOAT_MENU] = self._on_show_float_menu

        def _on_show_float_menu(self, _wparam, _lparam):
            app = self._tray_app
            if app is None:
                return 0
            if not self._menu_handle:
                self.update_menu()
            if not self._menu_handle:
                return 0

            x, y = app._float_menu_pos
            hmenu, callbacks = self._menu_handle
            pystray_win32.SetForegroundWindow(self._hwnd)
            index = pystray_win32.TrackPopupMenuEx(
                hmenu,
                pystray_win32.TPM_LEFTALIGN
                | pystray_win32.TPM_TOPALIGN
                | pystray_win32.TPM_RETURNCMD,
                int(x),
                int(y),
                self._menu_hwnd,
                None,
            )
            if index > 0:
                callbacks[index - 1](self)
            return 0

    return TrafficLightIcon
