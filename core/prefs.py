"""UI 偏好持久化（跨平台）"""
import json
import shutil
from pathlib import Path

from core.config import (
    DEFAULT_UI_PREFS,
    DISPLAY_FLOAT,
    DISPLAY_TRAY,
    UI_PREFS_FILE,
    UI_PREFS_FILE_LEGACY,
    normalize_theme,
)


def load_ui_prefs():
    """读取 UI 偏好（显示模式、透明度、浮窗位置）"""
    prefs = DEFAULT_UI_PREFS.copy()
    current = Path(UI_PREFS_FILE)
    legacy = Path(UI_PREFS_FILE_LEGACY)
    if not current.exists() and legacy.exists():
        try:
            current.parent.mkdir(parents=True, exist_ok=True)
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
    visible = prefs.get("visible_projects")
    if not isinstance(visible, list):
        prefs["visible_projects"] = []
    else:
        prefs["visible_projects"] = [str(project) for project in visible]
    prefs["theme"] = normalize_theme(prefs)
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
