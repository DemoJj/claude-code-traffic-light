"""浮窗 PIL 绘制（Windows 浮窗模式）"""
from core.config import (
    FLOAT_FONT,
    FLOAT_FRAME_PAD,
    FLOAT_GAP,
    FLOAT_INNER_PAD,
    FLOAT_LIGHT_DIAMETER,
    FLOAT_LIGHT_RADIUS,
    FLOAT_LIGHTS_BLOCK,
    FLOAT_LIGHTS_SPACING,
    FLOAT_NAME_MAX,
    FLOAT_RADIUS,
    FLOAT_ROW_HEIGHT,
    FLOAT_SCALE,
    FLOAT_WIDTH,
    get_float_theme,
)
from core.projects import calc_float_height
from core.rendering.colors import hex_to_rgb, light_fill, light_outline


def _get_pil_font(size):
    from PIL import ImageFont

    for name in ("segoeui.ttf", "Segoe UI.ttf", "msyh.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _truncate_pil_text(text, font, max_width):
    if not text:
        return "default"
    if font.getlength(text) <= max_width:
        return text
    ellipsis = "..."
    for end in range(len(text), 0, -1):
        candidate = text[:end] + ellipsis
        if font.getlength(candidate) <= max_width:
            return candidate
    return ellipsis


def _draw_float_row(draw, row_top, row_height, project_name, state, blink_on, font, scale, theme):
    """绘制浮窗中的单行项目"""
    pad = FLOAT_INNER_PAD * scale
    name_max = FLOAT_NAME_MAX * scale
    width = FLOAT_WIDTH * scale
    row_top_s = row_top * scale
    row_height_s = row_height * scale
    cy = row_top_s + row_height_s // 2
    separator_rgb = theme["separator_rgb"]
    text_rgb = theme["text_rgb"]
    light_dim_rgb = theme["light_dim_rgb"]
    outline_off_rgb = theme["light_outline_off_rgb"]

    if row_top > FLOAT_FRAME_PAD:
        draw.line(
            (pad, row_top_s, width - pad, row_top_s),
            fill=separator_rgb + (255,),
            width=scale,
        )

    separator_x = pad + name_max + (FLOAT_GAP * scale) // 2
    draw.line(
        (separator_x, row_top_s + 4 * scale, separator_x, row_top_s + row_height_s - 4 * scale),
        fill=separator_rgb + (255,),
        width=scale,
    )

    display_name = _truncate_pil_text(project_name, font, name_max - 4 * scale)
    draw.text((pad, cy), display_name, fill=text_rgb + (255,), font=font, anchor="lm")

    lights_start = width - pad - FLOAT_LIGHTS_BLOCK * scale
    light_r = FLOAT_LIGHT_RADIUS * scale
    for index, color_name in enumerate(["red", "yellow", "green"]):
        cx = lights_start + light_r + index * (FLOAT_LIGHT_DIAMETER + FLOAT_LIGHTS_SPACING) * scale
        fill_hex = light_fill(state, blink_on, color_name, light_dim_rgb)
        fill_rgb = hex_to_rgb(fill_hex)
        outline_hex = light_outline(state, blink_on, color_name, outline_off_rgb)
        outline_rgb = hex_to_rgb(outline_hex)
        active = state == color_name and (color_name != "yellow" or blink_on)
        if active:
            glow_r = light_r + scale
            glow = tuple(min(c + 30, 255) for c in fill_rgb)
            draw.ellipse(
                (cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r),
                fill=glow + (80,),
            )
        ellipse_box = (cx - light_r, cy - light_r, cx + light_r, cy + light_r)
        if theme.get("light_stroke", True):
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb + (255,),
                outline=outline_rgb + (255,),
                width=(2 if active else 1) * scale,
            )
        else:
            draw.ellipse(ellipse_box, fill=fill_rgb + (255,))


def render_float_surface(project_rows, blink_on, master=None, ui_prefs=None):
    """用 PIL 超采样绘制多项目浮窗"""
    from PIL import Image, ImageDraw, ImageTk

    if not project_rows:
        project_rows = [("default", "red")]

    theme = get_float_theme(ui_prefs)
    scale = FLOAT_SCALE
    width = FLOAT_WIDTH * scale
    height = calc_float_height(len(project_rows)) * scale
    img = Image.new("RGBA", (width, height), theme["transparent_rgb"] + (255,))
    draw = ImageDraw.Draw(img)

    radius = FLOAT_RADIUS * scale
    font = _get_pil_font(FLOAT_FONT[1] * scale)

    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=radius,
        fill=theme["bg_rgb"] + (255,),
        outline=theme["border_rgb"] + (255,),
        width=scale,
    )

    for index, (project_name, state) in enumerate(project_rows):
        row_top = FLOAT_FRAME_PAD + index * (FLOAT_ROW_HEIGHT + 1)
        _draw_float_row(
            draw,
            row_top,
            FLOAT_ROW_HEIGHT,
            project_name,
            state,
            blink_on,
            font,
            scale,
            theme,
        )

    out_h = calc_float_height(len(project_rows))
    img = img.resize((FLOAT_WIDTH, out_h), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img, master=master)
