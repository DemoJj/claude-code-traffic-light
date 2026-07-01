"""项目状态与可见性逻辑（跨平台）"""
import os
import shutil
from pathlib import Path

from core.config import FLOAT_MAX_ROWS, STATE_DIR, SELECTED_FILE
from core.prefs import load_ui_prefs, save_ui_prefs


def get_state_file(project_name=None):
    """获取指定项目的状态文件路径"""
    if project_name is None:
        project_name = get_selected_project()
    return os.path.join(STATE_DIR, f"{project_name}.state")


def get_selected_project():
    """获取当前选中的项目名，默认选中第一个活跃项目"""
    try:
        if Path(SELECTED_FILE).exists():
            return normalize_project_id(Path(SELECTED_FILE).read_text(encoding="utf-8").strip())
    except Exception:
        pass
    projects = list_active_projects()
    return projects[0] if projects else "default"


def set_selected_project(project_name):
    """设置当前选中的项目"""
    try:
        Path(SELECTED_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(SELECTED_FILE).write_text(project_name, encoding="utf-8")
    except Exception:
        pass


def normalize_project_id(project_id):
    """将旧盘符项目 ID（如 e:）规范为新格式 e_drive"""
    if not project_id:
        return project_id
    if len(project_id) == 2 and project_id[1] == ":" and project_id[0].isalpha():
        return f"{project_id[0].lower()}_drive"
    return project_id


def migrate_legacy_state_files():
    """迁移盘符根目录旧状态文件（e:.state → e_drive.state）并同步相关配置"""
    state_dir = Path(STATE_DIR)
    if not state_dir.exists():
        return

    for old_file in list(state_dir.glob("*.state")):
        stem = old_file.stem
        if len(stem) != 2 or stem[1] != ":" or not stem[0].isalpha():
            continue
        new_file = state_dir / f"{normalize_project_id(stem)}.state"
        try:
            if new_file.exists():
                if old_file.stat().st_mtime > new_file.stat().st_mtime:
                    shutil.copy2(old_file, new_file)
                old_file.unlink()
            else:
                old_file.rename(new_file)
        except Exception:
            pass

    selected_path = Path(SELECTED_FILE)
    if selected_path.exists():
        try:
            selected = selected_path.read_text(encoding="utf-8").strip()
            normalized = normalize_project_id(selected)
            if normalized != selected:
                selected_path.write_text(normalized, encoding="utf-8")
        except Exception:
            pass

    prefs = load_ui_prefs()
    visible = prefs.get("visible_projects")
    if not isinstance(visible, list):
        return

    new_visible = []
    changed = False
    for project in visible:
        normalized = normalize_project_id(str(project))
        if normalized != project:
            changed = True
        if normalized not in new_visible:
            new_visible.append(normalized)

    if changed:
        prefs["visible_projects"] = new_visible
        save_ui_prefs(prefs)


def list_active_projects():
    """列出所有有状态文件的项目"""
    try:
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
        return sorted(f.stem for f in Path(STATE_DIR).glob("*.state"))
    except Exception:
        return []


def display_project_name(project_id):
    """将内部项目 ID 转为可读名称（盘符根目录等）"""
    if not project_id:
        return "default"
    if project_id.endswith("_drive") and len(project_id) >= 7:
        letter = project_id[:-6]
        if len(letter) == 1 and letter.isalpha():
            return f"{letter.upper()}:\\"
    if len(project_id) == 2 and project_id[1] == ":" and project_id[0].isalpha():
        return f"{project_id[0].upper()}:\\"
    return project_id


def menu_project_label(project_id):
    """菜单标签：转义 &"""
    return display_project_name(project_id).replace("&", "&&")


def sync_visible_projects(ui_prefs):
    """同步可见项目：保留顺序、移除已结束项目、仅对新出现的项目自动勾选并追加到底部"""
    active = list_active_projects()
    active_set = set(active)
    visible = ui_prefs.get("visible_projects")
    if not isinstance(visible, list):
        visible = []

    last_active = ui_prefs.get("_last_active_projects")
    if not isinstance(last_active, list):
        last_active = []
    last_active_set = set(last_active)

    new_visible = [project for project in visible if project in active_set]

    if not visible and active:
        new_visible = list(active)
    else:
        for project in active:
            if project not in new_visible and project not in last_active_set:
                new_visible.append(project)

    changed = new_visible != visible or active != last_active
    ui_prefs["visible_projects"] = new_visible
    ui_prefs["_last_active_projects"] = active
    if changed:
        save_ui_prefs(ui_prefs)
    return new_visible


def get_tray_project(ui_prefs):
    """菜单「当前项目」显示用（可见列表中的第一个）"""
    visible = sync_visible_projects(ui_prefs)
    if visible:
        return visible[0]
    projects = list_active_projects()
    if projects:
        return projects[0]
    return get_selected_project()


def get_tray_aggregate_projects(ui_prefs=None):
    """参与托盘/菜单栏聚合亮灯的项目列表"""
    if ui_prefs is not None:
        return sync_visible_projects(ui_prefs)
    selected = get_selected_project()
    return [selected] if selected else []


def read_project_state(project_name):
    """读取单个项目的状态"""
    try:
        state_file = get_state_file(project_name)
        if Path(state_file).exists():
            content = Path(state_file).read_text(encoding="utf-8").strip().lower()
            if content in ("green", "yellow", "red"):
                return content
    except Exception:
        pass
    return "red"


def aggregate_tray_state(project_names):
    """聚合托盘灯色：全绿→绿；任一黄→黄；全红→红；其余按有黄优先、有绿次之"""
    if not project_names:
        return "red"
    states = [read_project_state(name) for name in project_names]
    if any(state == "yellow" for state in states):
        return "yellow"
    if all(state == "green" for state in states):
        return "green"
    if all(state == "red" for state in states):
        return "red"
    if any(state == "green" for state in states):
        return "green"
    return "red"


def build_float_project_rows(ui_prefs=None):
    """构建浮窗多行项目数据：(显示名, 状态)"""
    if ui_prefs is None:
        ui_prefs = load_ui_prefs()
    visible = sync_visible_projects(ui_prefs)
    if not visible:
        if not list_active_projects():
            return [("default", "red")]
        return [("(无显示项目)", "red")]

    rows = []
    for name in visible[:FLOAT_MAX_ROWS]:
        rows.append((display_project_name(name), read_project_state(name)))
    extra = len(visible) - FLOAT_MAX_ROWS
    if extra > 0:
        rows.append((f"... 还有 {extra} 个项目", "red"))
    return rows


def calc_float_height(num_rows):
    """根据项目行数计算浮窗高度"""
    from core.config import FLOAT_FRAME_PAD, FLOAT_ROW_HEIGHT

    num_rows = max(1, num_rows)
    return FLOAT_FRAME_PAD * 2 + num_rows * FLOAT_ROW_HEIGHT + max(0, num_rows - 1)
