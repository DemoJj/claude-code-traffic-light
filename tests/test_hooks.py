"""hooks 模块：Claude Code hook 合并与识别"""
import json

from core.config import HOOK_STATE_DIR, TRAFFIC_MARKER
from core.hooks import _hook_cmd, _is_traffic_hook, configure_hooks


def test_is_traffic_hook_by_marker():
    entry = {"hooks": [{"command": f"echo red # {TRAFFIC_MARKER}"}]}
    assert _is_traffic_hook(entry) is True


def test_is_traffic_hook_by_state_dir():
    entry = {"hooks": [{"command": f"echo green > {HOOK_STATE_DIR}/p.state"}]}
    assert _is_traffic_hook(entry) is True


def test_is_traffic_hook_rejects_foreign():
    entry = {"hooks": [{"command": "echo hello"}]}
    assert _is_traffic_hook(entry) is False


def test_hook_cmd_contains_marker_and_state_dir():
    cmd = _hook_cmd("yellow")
    assert TRAFFIC_MARKER in cmd
    assert HOOK_STATE_DIR in cmd
    assert "echo yellow" in cmd
    assert "_drive" in cmd


def test_configure_hooks_merges_and_preserves_foreign(claude_home):
    foreign = {
        "matcher": "",
        "hooks": [{"type": "command", "command": "echo keep-me"}],
    }
    claude_home["config"].parent.mkdir(parents=True, exist_ok=True)
    claude_home["config"].write_text(
        json.dumps({"hooks": {"Stop": [foreign]}}),
        encoding="utf-8",
    )

    configure_hooks()

    config = json.loads(claude_home["config"].read_text(encoding="utf-8"))
    stop_hooks = config["hooks"]["Stop"]
    commands = [h["hooks"][0]["command"] for h in stop_hooks]
    assert any("keep-me" in cmd for cmd in commands)
    assert any(TRAFFIC_MARKER in cmd for cmd in commands)
    assert len(stop_hooks) == 2


def test_configure_hooks_replaces_old_traffic_hooks(claude_home):
    old_traffic = {
        "matcher": "",
        "hooks": [{"type": "command", "command": f"echo red # {TRAFFIC_MARKER}"}],
    }
    claude_home["config"].parent.mkdir(parents=True, exist_ok=True)
    claude_home["config"].write_text(
        json.dumps({"hooks": {"Stop": [old_traffic, old_traffic]}}),
        encoding="utf-8",
    )

    configure_hooks()

    config = json.loads(claude_home["config"].read_text(encoding="utf-8"))
    stop_hooks = config["hooks"]["Stop"]
    traffic_count = sum(
        1 for entry in stop_hooks if _is_traffic_hook(entry)
    )
    assert traffic_count == 1


def test_configure_hooks_sets_all_events(claude_home):
    configure_hooks()
    config = json.loads(claude_home["config"].read_text(encoding="utf-8"))
    expected = {
        "SessionStart",
        "UserPromptSubmit",
        "PermissionRequest",
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SessionEnd",
    }
    assert expected.issubset(config["hooks"].keys())
