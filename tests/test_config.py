"""config 模块：主题与常量校验"""
from core.config import (
    DEFAULT_UI_PREFS,
    FLOAT_THEME_PRESETS,
    THEME_DARK,
    THEME_LIGHT,
    get_float_theme,
    normalize_theme,
)


def test_normalize_theme_defaults_to_dark():
    assert normalize_theme({}) == THEME_DARK
    assert normalize_theme({"theme": THEME_LIGHT}) == THEME_LIGHT


def test_normalize_theme_rejects_invalid():
    assert normalize_theme({"theme": "neon"}) == THEME_DARK
    assert normalize_theme({"theme": None}) == THEME_DARK


def test_get_float_theme_returns_preset():
    dark = get_float_theme({"theme": THEME_DARK})
    light = get_float_theme({"theme": THEME_LIGHT})
    assert dark is FLOAT_THEME_PRESETS[THEME_DARK]
    assert light is FLOAT_THEME_PRESETS[THEME_LIGHT]
    assert dark["light_stroke"] is True
    assert light["light_stroke"] is False


def test_default_ui_prefs_has_required_keys():
    assert DEFAULT_UI_PREFS["display_mode"] == "tray"
    assert DEFAULT_UI_PREFS["theme"] == THEME_DARK
    assert DEFAULT_UI_PREFS["visible_projects"] == []
