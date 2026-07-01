"""Windows 浮窗（tkinter Toplevel）"""
from core.config import FLOAT_TRANSPARENT, FLOAT_WIDTH
from core.prefs import save_ui_prefs
from core.projects import build_float_project_rows, calc_float_height
from core.rendering.float_surface import render_float_surface
from core.windows.work_area import get_monitor_work_area


class FloatWindow:
    """置顶浮窗，可拖拽、可调透明度（主线程 Toplevel）"""

    def __init__(self, prefs, app):
        self._app = app
        self._drag_offset = (0, 0)
        self._prefs = prefs
        self._visible = False
        self._project_rows = []
        self._blink_on = True
        self._current_height = calc_float_height(1)
        self._tk_image = None
        self.root = None
        self._label = None

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
        self._current_height = calc_float_height(1)
        root.geometry(f"{FLOAT_WIDTH}x{self._current_height}")

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
        if not self._project_rows:
            self._project_rows = build_float_project_rows(
                self._app.ui_prefs if self._app else None
            )
        new_height = calc_float_height(len(self._project_rows))
        ui_prefs = self._app.ui_prefs if self._app else None
        self._tk_image = render_float_surface(
            self._project_rows,
            self._blink_on,
            master=self.root,
            ui_prefs=ui_prefs,
        )
        self._label.config(image=self._tk_image)
        if new_height != self._current_height:
            self._current_height = new_height
            self._apply_position()

    def _clamp_position(self, x, y):
        if self.root is None:
            return int(x), int(y)
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), FLOAT_WIDTH)
        height = max(self.root.winfo_height(), self._current_height)
        work_left, work_top, work_right, work_bottom = get_monitor_work_area(x, y, width, height)
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
        self.root.geometry(f"{FLOAT_WIDTH}x{self._current_height}+{x}+{y}")

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

    def _on_right_click(self, event):
        self._app.show_native_context_menu(event.x_root, event.y_root)
        return "break"

    def _show_impl(self):
        self._apply_position()
        self.root.deiconify()
        self._visible = True

    def _hide_impl(self):
        self.root.withdraw()
        self._visible = False

    def _update_impl(self, project_rows, blink_on, opacity):
        self._project_rows = project_rows
        self._blink_on = blink_on
        self._render_surface()
        self._apply_opacity(opacity)

    def show(self):
        self._dispatch(self._show_impl)

    def hide(self):
        self._dispatch(self._hide_impl)

    def update(self, project_rows, blink_on, opacity):
        self._dispatch(self._update_impl, project_rows, blink_on, opacity)

    def destroy(self):
        self._dispatch(self._destroy_impl)

    def _destroy_impl(self):
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
