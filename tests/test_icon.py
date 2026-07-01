"""rendering.icon 模块：菜单栏标题格式化"""
from core.config import LIGHT_OFF, LIGHT_ON
from core.rendering.icon import format_title


def test_format_title_green():
    title = format_title("green", True)
    assert LIGHT_ON["green"] in title
    assert title.count(LIGHT_OFF) == 2


def test_format_title_red():
    title = format_title("red", True)
    assert LIGHT_ON["red"] in title
    assert title.count(LIGHT_OFF) == 2


def test_format_title_yellow_blinks():
    on = format_title("yellow", True)
    off = format_title("yellow", False)
    assert LIGHT_ON["yellow"] in on
    assert LIGHT_ON["yellow"] not in off
    assert LIGHT_OFF in off
