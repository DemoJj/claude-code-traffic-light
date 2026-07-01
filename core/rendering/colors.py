"""红绿灯颜色与绘制工具（跨平台）"""
from core.config import LIGHT_COLORS, LIGHT_DIM


def rgb_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def light_fill(state, blink_on, color_name, light_dim_rgb=LIGHT_DIM):
    if state == color_name:
        if color_name == "yellow" and not blink_on:
            return rgb_hex(light_dim_rgb)
        return rgb_hex(LIGHT_COLORS[color_name])
    return rgb_hex(light_dim_rgb)


def light_outline(state, blink_on, color_name, outline_off_rgb=(51, 51, 51)):
    if state == color_name and (color_name != "yellow" or blink_on):
        r, g, b = LIGHT_COLORS[color_name]
        return f"#{min(r + 40, 255):02x}{min(g + 40, 255):02x}{min(b + 40, 255):02x}"
    return rgb_hex(outline_off_rgb)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
