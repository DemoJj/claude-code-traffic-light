"""projects 模块：项目名、可见性同步、状态聚合"""
import sys

import pytest
from core.projects import (
    aggregate_tray_state,
    build_float_project_rows,
    calc_float_height,
    display_project_name,
    get_state_file,
    get_tray_aggregate_projects,
    list_active_projects,
    menu_project_label,
    migrate_legacy_state_files,
    normalize_project_id,
    read_project_state,
    sync_visible_projects,
)

from tests.conftest import write_state


class TestNormalizeProjectId:
    def test_drive_colon_form(self):
        assert normalize_project_id("e:") == "e_drive"
        assert normalize_project_id("E:") == "e_drive"

    def test_other_unchanged(self):
        assert normalize_project_id("my-app") == "my-app"
        assert normalize_project_id("e_drive") == "e_drive"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows 文件名不支持冒号")
class TestMigrateLegacyStateFiles:
    def test_renames_drive_colon_state_file(self, claude_home):
        write_state(claude_home["state_dir"], "e:", "green")
        migrate_legacy_state_files()
        assert list_active_projects() == ["e_drive"]
        assert read_project_state("e_drive") == "green"
        assert not (claude_home["state_dir"] / "e:.state").exists()

    def test_keeps_newer_state_when_both_exist(self, claude_home):
        write_state(claude_home["state_dir"], "e:", "red")
        write_state(claude_home["state_dir"], "e_drive", "green")
        old = claude_home["state_dir"] / "e:.state"
        import os
        import time

        os.utime(old, (time.time() + 10, time.time() + 10))
        migrate_legacy_state_files()
        assert read_project_state("e_drive") == "red"
        assert list_active_projects() == ["e_drive"]


def test_migrates_selected_and_visible_prefs(claude_home):
    claude_home["selected"].write_text("e:", encoding="utf-8")
    claude_home["ui_prefs"].write_text(
        '{"visible_projects": ["e:", "other"]}',
        encoding="utf-8",
    )
    migrate_legacy_state_files()
    assert claude_home["selected"].read_text(encoding="utf-8") == "e_drive"
    from core.prefs import load_ui_prefs

    prefs = load_ui_prefs()
    assert prefs["visible_projects"] == ["e_drive", "other"]


class TestDisplayProjectName:
    def test_empty_returns_default(self):
        assert display_project_name("") == "default"
        assert display_project_name(None) == "default"

    def test_drive_suffix(self):
        assert display_project_name("e_drive") == "E:\\"
        assert display_project_name("c_drive") == "C:\\"

    def test_colon_form(self):
        assert display_project_name("e:") == "E:\\"

    def test_plain_name_unchanged(self):
        assert display_project_name("my-app") == "my-app"


class TestMenuProjectLabel:
    def test_escapes_ampersand(self):
        assert menu_project_label("foo&bar") == "foo&&bar"


class TestStateFiles:
    def test_get_state_file_path(self, claude_home):
        path = get_state_file("demo")
        assert path.endswith("demo.state")
        assert claude_home["state_dir"].name == "traffic_light"

    def test_list_active_projects_sorted(self, claude_home):
        write_state(claude_home["state_dir"], "beta", "green")
        write_state(claude_home["state_dir"], "alpha", "red")
        assert list_active_projects() == ["alpha", "beta"]

    def test_read_project_state_valid_and_invalid(self, claude_home):
        write_state(claude_home["state_dir"], "p1", "green")
        assert read_project_state("p1") == "green"
        write_state(claude_home["state_dir"], "p2", "UNKNOWN")
        assert read_project_state("p2") == "red"
        assert read_project_state("missing") == "red"


class TestSyncVisibleProjects:
    def test_first_run_selects_all_active(self, claude_home):
        write_state(claude_home["state_dir"], "a", "green")
        write_state(claude_home["state_dir"], "b", "red")
        prefs = {"visible_projects": []}
        visible = sync_visible_projects(prefs)
        assert visible == ["a", "b"]

    def test_removes_inactive_projects(self, claude_home):
        write_state(claude_home["state_dir"], "active", "green")
        prefs = {
            "visible_projects": ["gone", "active"],
            "_last_active_projects": ["gone", "active"],
        }
        visible = sync_visible_projects(prefs)
        assert visible == ["active"]

    def test_new_project_appended_to_bottom(self, claude_home):
        write_state(claude_home["state_dir"], "old", "green")
        write_state(claude_home["state_dir"], "new", "yellow")
        prefs = {
            "visible_projects": ["old"],
            "_last_active_projects": ["old"],
        }
        visible = sync_visible_projects(prefs)
        assert visible == ["old", "new"]

    def test_preserves_user_order_without_readding_hidden(self, claude_home):
        write_state(claude_home["state_dir"], "a", "green")
        write_state(claude_home["state_dir"], "b", "green")
        write_state(claude_home["state_dir"], "c", "green")
        prefs = {
            "visible_projects": ["c", "a"],
            "_last_active_projects": ["a", "b", "c"],
        }
        visible = sync_visible_projects(prefs)
        assert visible == ["c", "a"]


class TestTrayAggregateProjects:
    def test_without_ui_prefs_uses_selected_only(self, claude_home):
        write_state(claude_home["state_dir"], "selected", "green")
        write_state(claude_home["state_dir"], "other", "yellow")
        claude_home["selected"].write_text("selected", encoding="utf-8")
        assert get_tray_aggregate_projects() == ["selected"]

    def test_empty_visible_does_not_fallback_to_all_active(self, claude_home):
        write_state(claude_home["state_dir"], "proj", "green")
        prefs = {
            "visible_projects": ["removed"],
            "_last_active_projects": ["removed", "proj"],
        }
        assert get_tray_aggregate_projects(prefs) == []


class TestAggregateTrayState:
    def test_empty_is_red(self):
        assert aggregate_tray_state([]) == "red"

    def test_any_yellow_wins(self, claude_home):
        write_state(claude_home["state_dir"], "p1", "green")
        write_state(claude_home["state_dir"], "p2", "yellow")
        assert aggregate_tray_state(["p1", "p2"]) == "yellow"

    def test_all_green(self, claude_home):
        write_state(claude_home["state_dir"], "p1", "green")
        write_state(claude_home["state_dir"], "p2", "green")
        assert aggregate_tray_state(["p1", "p2"]) == "green"

    def test_all_red(self, claude_home):
        write_state(claude_home["state_dir"], "p1", "red")
        write_state(claude_home["state_dir"], "p2", "red")
        assert aggregate_tray_state(["p1", "p2"]) == "red"

    def test_mixed_green_red_is_green(self, claude_home):
        write_state(claude_home["state_dir"], "p1", "green")
        write_state(claude_home["state_dir"], "p2", "red")
        assert aggregate_tray_state(["p1", "p2"]) == "green"


class TestFloatRows:
    def test_no_active_shows_default(self, claude_home):
        rows = build_float_project_rows({"visible_projects": []})
        assert rows == [("default", "red")]

    def test_all_visible_removed_shows_hint(self, claude_home):
        write_state(claude_home["state_dir"], "proj", "green")
        prefs = {
            "visible_projects": ["removed"],
            "_last_active_projects": ["removed", "proj"],
        }
        rows = build_float_project_rows(prefs)
        assert rows == [("(无显示项目)", "red")]

    def test_drive_name_in_rows(self, claude_home):
        write_state(claude_home["state_dir"], "e_drive", "yellow")
        prefs = {"visible_projects": ["e_drive"], "_last_active_projects": ["e_drive"]}
        rows = build_float_project_rows(prefs)
        assert rows == [("E:\\", "yellow")]

    def test_calc_float_height(self):
        assert calc_float_height(1) == 34
        assert calc_float_height(2) == 61
        assert calc_float_height(0) == 34
