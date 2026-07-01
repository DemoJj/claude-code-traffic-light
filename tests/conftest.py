"""测试夹具：将 Claude 配置与状态目录重定向到临时路径"""
from pathlib import Path

import pytest


@pytest.fixture
def claude_home(tmp_path, monkeypatch):
    """隔离 ~/.claude 相关路径，避免污染真实环境"""
    traffic_light = tmp_path / ".claude" / "traffic_light"
    traffic_light.mkdir(parents=True)

    state_dir = str(traffic_light)
    ui_prefs = str(traffic_light / "ui_prefs.json")
    ui_prefs_legacy = str(tmp_path / ".claude" / "traffic_light_ui.json")
    selected = str(traffic_light / "selected_project")
    config = str(tmp_path / ".claude" / "settings.json")
    backup = str(traffic_light / "settings_backup.json")

    import core.config as config_mod
    import core.hooks as hooks_mod
    import core.monitor as monitor_mod
    import core.prefs as prefs_mod
    import core.projects as projects_mod

    patches = {
        "STATE_DIR": state_dir,
        "BASE_DIR": state_dir,
        "SELECTED_FILE": selected,
        "UI_PREFS_FILE": ui_prefs,
        "UI_PREFS_FILE_LEGACY": ui_prefs_legacy,
        "CONFIG_PATH": config,
        "BACKUP_PATH": backup,
    }
    for module in (config_mod, projects_mod, prefs_mod, hooks_mod, monitor_mod):
        for name, value in patches.items():
            if hasattr(module, name):
                monkeypatch.setattr(module, name, value)

    paths = {
        "home": tmp_path,
        "state_dir": traffic_light,
        "ui_prefs": Path(ui_prefs),
        "ui_prefs_legacy": Path(ui_prefs_legacy),
        "config": Path(config),
        "backup": Path(backup),
        "selected": Path(selected),
    }
    return paths


def write_state(state_dir: Path, project: str, state: str) -> None:
    """写入单个项目状态文件"""
    (state_dir / f"{project}.state").write_text(state, encoding="utf-8")
