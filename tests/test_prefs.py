"""prefs 模块：UI 偏好读写与校验"""
import json

from core.config import DISPLAY_FLOAT, DISPLAY_TRAY, THEME_LIGHT
from core.prefs import load_ui_prefs, save_ui_prefs


def test_load_defaults_when_missing(claude_home):
    prefs = load_ui_prefs()
    assert prefs["display_mode"] == DISPLAY_TRAY
    assert prefs["opacity"] == 0.85
    assert prefs["visible_projects"] == []


def test_save_and_reload(claude_home):
    prefs = load_ui_prefs()
    prefs["display_mode"] = DISPLAY_FLOAT
    prefs["opacity"] = 0.5
    prefs["visible_projects"] = ["proj-a"]
    prefs["theme"] = THEME_LIGHT
    save_ui_prefs(prefs)

    loaded = load_ui_prefs()
    assert loaded["display_mode"] == DISPLAY_FLOAT
    assert loaded["opacity"] == 0.5
    assert loaded["visible_projects"] == ["proj-a"]
    assert loaded["theme"] == THEME_LIGHT


def test_invalid_display_mode_reset(claude_home):
    claude_home["ui_prefs"].write_text(
        json.dumps({"display_mode": "popup"}),
        encoding="utf-8",
    )
    assert load_ui_prefs()["display_mode"] == DISPLAY_TRAY


def test_opacity_clamped(claude_home):
    claude_home["ui_prefs"].write_text(
        json.dumps({"opacity": 5.0}),
        encoding="utf-8",
    )
    assert load_ui_prefs()["opacity"] == 1.0

    claude_home["ui_prefs"].write_text(
        json.dumps({"opacity": "bad"}),
        encoding="utf-8",
    )
    assert load_ui_prefs()["opacity"] == 0.85


def test_migrates_legacy_prefs_file(claude_home):
    claude_home["ui_prefs_legacy"].parent.mkdir(parents=True, exist_ok=True)
    claude_home["ui_prefs_legacy"].write_text(
        json.dumps({"opacity": 0.3}),
        encoding="utf-8",
    )
    prefs = load_ui_prefs()
    assert prefs["opacity"] == 0.3
    assert claude_home["ui_prefs"].exists()
