"""路径、常量与主题配置（跨平台共享）"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
ICON_ICNS_PATH = ASSETS_DIR / "icon.icns"

BASE_DIR = str(Path.home() / ".claude" / "traffic_light")
STATE_DIR = BASE_DIR
CONFIG_PATH = str(Path.home() / ".claude" / "settings.json")
BACKUP_PATH = os.path.join(BASE_DIR, "settings_backup.json")
SELECTED_FILE = os.path.join(BASE_DIR, "selected_project")
UI_PREFS_FILE = os.path.join(BASE_DIR, "ui_prefs.json")
UI_PREFS_FILE_LEGACY = str(Path.home() / ".claude" / "traffic_light_ui.json")
# Claude Code 在 Windows 上也通过 Git Bash 执行 hook，路径必须用 POSIX 格式
HOOK_STATE_DIR = "~/.claude/traffic_light"

POLL_INTERVAL = 0.3
BLINK_INTERVAL = 0.5
MENU_REFRESH_INTERVAL = 2

DISPLAY_TRAY = "tray"
DISPLAY_FLOAT = "float"
THEME_DARK = "dark"
THEME_LIGHT = "light"
OPACITY_PRESETS = [0.3, 0.5, 0.7, 0.85, 1.0]
DEFAULT_UI_PREFS = {
    "display_mode": DISPLAY_TRAY,
    "opacity": 0.85,
    "float_x": None,
    "float_y": None,
    "visible_projects": [],
    "theme": THEME_DARK,
}

TRAFFIC_MARKER = "traffic_light_app"

LIGHT_ON = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
LIGHT_OFF = "⚫"

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
FLOAT_ROW_HEIGHT = 26
FLOAT_FRAME_PAD = 4
FLOAT_MAX_ROWS = 12
FLOAT_RADIUS = 12
FLOAT_FONT = ("Segoe UI", 11)
FLOAT_SCALE = 3
FLOAT_BG_RGB = (43, 43, 43)
FLOAT_BORDER_RGB = (69, 69, 69)
FLOAT_TRANSPARENT_RGB = (1, 1, 2)
FLOAT_SEPARATOR_RGB = (69, 69, 69)
FLOAT_TEXT_RGB = (232, 232, 232)

FLOAT_THEME_PRESETS = {
    THEME_DARK: {
        "bg_rgb": FLOAT_BG_RGB,
        "border_rgb": FLOAT_BORDER_RGB,
        "separator_rgb": FLOAT_SEPARATOR_RGB,
        "text_rgb": FLOAT_TEXT_RGB,
        "light_dim_rgb": LIGHT_DIM,
        "light_outline_off_rgb": (51, 51, 51),
        "light_stroke": True,
        "transparent": FLOAT_TRANSPARENT,
        "transparent_rgb": FLOAT_TRANSPARENT_RGB,
    },
    THEME_LIGHT: {
        "bg_rgb": (248, 248, 248),
        "border_rgb": (190, 190, 190),
        "separator_rgb": (210, 210, 210),
        "text_rgb": (30, 30, 30),
        "light_dim_rgb": (195, 195, 195),
        "light_outline_off_rgb": (165, 165, 165),
        "light_stroke": False,
        "transparent": FLOAT_TRANSPARENT,
        "transparent_rgb": FLOAT_TRANSPARENT_RGB,
    },
}


def normalize_theme(ui_prefs):
    """读取并校验主题偏好"""
    theme = ui_prefs.get("theme", THEME_DARK)
    if theme not in FLOAT_THEME_PRESETS:
        theme = THEME_DARK
    return theme


def get_float_theme(ui_prefs=None):
    """获取浮窗绘制主题配色"""
    if ui_prefs is None:
        return FLOAT_THEME_PRESETS[THEME_DARK]
    return FLOAT_THEME_PRESETS[normalize_theme(ui_prefs)]
