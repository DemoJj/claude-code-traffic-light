"""monitor 模块：StateMonitor 轮询逻辑"""
import json
import time

from core.monitor import StateMonitor, load_claude_info

from tests.conftest import write_state


def test_load_claude_info_from_config(claude_home):
    claude_home["config"].parent.mkdir(parents=True, exist_ok=True)
    claude_home["config"].write_text(
        json.dumps({"env": {"ANTHROPIC_MODEL": "claude-test"}}),
        encoding="utf-8",
    )
    info = load_claude_info()
    assert info["model"] == "claude-test"


def test_load_claude_info_default_when_missing(claude_home):
    assert load_claude_info()["model"] == "未知"


def test_check_state_updates_on_file_change(claude_home):
    write_state(claude_home["state_dir"], "default", "green")
    claude_home["selected"].write_text("default", encoding="utf-8")

    monitor = StateMonitor()
    changed, _ = monitor.check_state()
    assert changed is True
    assert monitor.state == "green"

    write_state(claude_home["state_dir"], "default", "yellow")
    changed, _ = monitor.check_state()
    assert changed is True
    assert monitor.state == "yellow"


def test_check_state_without_ui_prefs_uses_selected_project(claude_home):
    write_state(claude_home["state_dir"], "selected", "green")
    write_state(claude_home["state_dir"], "other", "yellow")
    claude_home["selected"].write_text("selected", encoding="utf-8")

    monitor = StateMonitor()
    monitor.check_state()
    assert monitor.state == "green"


def test_check_state_respects_visible_projects(claude_home):
    write_state(claude_home["state_dir"], "visible", "green")
    write_state(claude_home["state_dir"], "hidden", "yellow")
    prefs = {
        "visible_projects": ["visible"],
        "_last_active_projects": ["visible", "hidden"],
    }

    monitor = StateMonitor()
    monitor.check_state(prefs)
    assert monitor.state == "green"


def test_select_project_resets_to_red(claude_home):
    write_state(claude_home["state_dir"], "other", "green")
    monitor = StateMonitor()
    monitor.check_state()
    monitor.select_project("other")
    assert monitor.state == "red"
    assert monitor.selected_project == "other"
    assert claude_home["selected"].read_text(encoding="utf-8") == "other"


def test_toggle_blink_flips_flag(claude_home):
    monitor = StateMonitor()
    calls = []
    monitor.set_on_state_change(lambda: calls.append(monitor.blink_on))
    monitor.toggle_blink()
    assert monitor.blink_on is False
    assert calls == [False]
    monitor.toggle_blink()
    assert monitor.blink_on is True


def test_menu_refresh_on_project_list_change(claude_home, monkeypatch):
    write_state(claude_home["state_dir"], "a", "red")
    monitor = StateMonitor()
    monitor.last_menu_build_time = 0
    changed, menu_refresh = monitor.check_state()
    assert menu_refresh is True
    assert changed is True

    monitor.last_menu_build_time = time.time()
    changed, menu_refresh = monitor.check_state()
    assert menu_refresh is False
