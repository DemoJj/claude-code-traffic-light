"""Claude Code hooks 配置与清理（跨平台）"""
import json
import os
import shutil
from pathlib import Path

from core.config import (
    BACKUP_PATH,
    CONFIG_PATH,
    HOOK_STATE_DIR,
    SELECTED_FILE,
    STATE_DIR,
    TRAFFIC_MARKER,
    UI_PREFS_FILE,
    UI_PREFS_FILE_LEGACY,
)

_restored = False


def backup_config():
    """备份原始配置文件"""
    if Path(CONFIG_PATH).exists():
        try:
            shutil.copy2(CONFIG_PATH, BACKUP_PATH)
            print(f"已备份原始配置: {BACKUP_PATH}")
            return True
        except Exception as e:
            print(f"备份配置失败: {e}")
    return True


def restore_config():
    """还原备份的配置文件并清理所有新增文件"""
    global _restored
    if _restored:
        return
    _restored = True

    if Path(BACKUP_PATH).exists():
        try:
            shutil.copy2(BACKUP_PATH, CONFIG_PATH)
            Path(BACKUP_PATH).unlink()
            print(f"已还原原始配置: {CONFIG_PATH}")
        except Exception as e:
            print(f"还原配置失败: {e}")

    ui_prefs_path = Path(UI_PREFS_FILE)
    ui_prefs_text = None
    if ui_prefs_path.exists():
        try:
            ui_prefs_text = ui_prefs_path.read_text(encoding="utf-8")
        except Exception:
            pass

    if Path(STATE_DIR).exists():
        try:
            shutil.rmtree(STATE_DIR)
            print(f"已清理状态目录: {STATE_DIR}")
        except Exception as e:
            print(f"清理状态目录失败: {e}")

    if ui_prefs_text is not None:
        try:
            ui_prefs_path.parent.mkdir(parents=True, exist_ok=True)
            ui_prefs_path.write_text(ui_prefs_text, encoding="utf-8")
        except Exception as e:
            print(f"保留 UI 偏好失败: {e}")

    if Path(UI_PREFS_FILE_LEGACY).exists():
        try:
            Path(UI_PREFS_FILE_LEGACY).unlink()
        except Exception:
            pass

    if Path(SELECTED_FILE).exists():
        try:
            Path(SELECTED_FILE).unlink()
            print(f"已清理选择文件: {SELECTED_FILE}")
        except Exception as e:
            print(f"清理选择文件失败: {e}")

    old_file = os.path.expanduser("~/.claude/.traffic_light")
    if Path(old_file).exists():
        try:
            Path(old_file).unlink()
            print(f"已清理旧版状态文件: {old_file}")
        except Exception:
            pass


def _is_traffic_hook(entry):
    """判断一个 hook 条目是否属于红绿灯"""
    for hook in entry.get("hooks", []):
        cmd = hook.get("command", "")
        if TRAFFIC_MARKER in cmd or HOOK_STATE_DIR in cmd:
            return True
    return False


def _make_hook_entry(command, matcher=""):
    """创建一个符合 Claude Code 格式的 hook 条目"""
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": command}],
    }


def _hook_cmd(state):
    """生成 hook 命令（Claude Code 在 macOS/Windows 上均通过 bash 执行）"""
    marker = f"# {TRAFFIC_MARKER}"
    return (
        f'project=$(basename "${{CLAUDE_PROJECT_DIR:-$PWD}}") && '
        f'if [ -z "$project" ] || [ "$project" = "." ]; then project=default; fi && '
        f'case "$project" in *:*) project="${{project%:}}_drive";; esac && '
        f'mkdir -p {HOOK_STATE_DIR} && echo {state} > {HOOK_STATE_DIR}/"$project".state {marker}'
    )


def configure_hooks():
    """安全地将所需的 hook 合并到 ~/.claude/settings.json"""
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(STATE_DIR).mkdir(parents=True, exist_ok=True)

    from core.projects import migrate_legacy_state_files

    migrate_legacy_state_files()

    backup_config()

    config = {}
    if Path(CONFIG_PATH).exists():
        try:
            config = json.loads(Path(CONFIG_PATH).read_text(encoding="utf-8"))
        except Exception:
            config = {}

    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}

    hook_cmd = _hook_cmd
    permission_tools = "Bash|Write|Edit|NotebookEdit|WebFetch"

    desired = {
        "SessionStart": [_make_hook_entry(hook_cmd("red"))],
        "UserPromptSubmit": [_make_hook_entry(hook_cmd("green"))],
        "PermissionRequest": [_make_hook_entry(hook_cmd("yellow"))],
        "PreToolUse": [_make_hook_entry(hook_cmd("yellow"), matcher=permission_tools)],
        "PostToolUse": [_make_hook_entry(hook_cmd("green"), matcher=permission_tools)],
        "Stop": [_make_hook_entry(hook_cmd("red"))],
        "SessionEnd": [_make_hook_entry(hook_cmd("red"))],
    }

    for hook_name, new_entries in desired.items():
        existing = hooks.get(hook_name, [])
        if not isinstance(existing, list):
            existing = []
        cleaned = [entry for entry in existing if not _is_traffic_hook(entry)]
        cleaned.extend(new_entries)
        hooks[hook_name] = cleaned
        print(f"已设置 hook: {hook_name}")

    config["hooks"] = hooks
    try:
        Path(CONFIG_PATH).write_text(
            json.dumps(config, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Claude Code 配置已更新: {CONFIG_PATH}")
    except Exception as e:
        print(f"写入配置失败: {e}")
