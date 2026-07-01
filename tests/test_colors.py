"""rendering.colors 模块：灯色与描边计算"""
from core.config import LIGHT_COLORS, LIGHT_DIM
from core.rendering.colors import hex_to_rgb, light_fill, light_outline, rgb_hex


def test_rgb_hex():
    assert rgb_hex((255, 0, 128)) == "#ff0080"


def test_hex_to_rgb():
    assert hex_to_rgb("#ff0080") == (255, 0, 128)
    assert hex_to_rgb("ff0080") == (255, 0, 128)


def test_light_fill_active_colors():
    assert light_fill("green", True, "green") == rgb_hex(LIGHT_COLORS["green"])
    assert light_fill("red", True, "red") == rgb_hex(LIGHT_COLORS["red"])


def test_light_fill_yellow_blink_off_is_dim():
    dim = rgb_hex(LIGHT_DIM)
    assert light_fill("yellow", False, "yellow") == dim
    assert light_fill("yellow", True, "yellow") == rgb_hex(LIGHT_COLORS["yellow"])


def test_light_fill_inactive_is_dim():
    dim = rgb_hex(LIGHT_DIM)
    assert light_fill("green", True, "red") == dim


def test_light_outline_yellow_blink_off_uses_off_color():
    off = rgb_hex((51, 51, 51))
    assert light_outline("yellow", False, "yellow") == off


def test_light_outline_active_brightens():
    outline = light_outline("green", True, "green")
    r, g, b = hex_to_rgb(outline)
    assert r >= LIGHT_COLORS["green"][0]
    assert g >= LIGHT_COLORS["green"][1]
