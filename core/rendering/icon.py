"""托盘图标与 macOS 标题渲染（跨平台）"""
from core.config import HOUSING_COLOR, LIGHT_OFF, LIGHT_ON
from core.rendering.colors import light_fill


def render_traffic_icon(state, blink_on):
    """绘制托盘/图标用红绿灯图像"""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    housing = (18, 8, 46, 56)
    draw.rounded_rectangle(housing, radius=8, fill=HOUSING_COLOR)

    cx = 32
    positions = [("red", 20), ("yellow", 32), ("green", 44)]
    for color_name, cy in positions:
        fill_hex = light_fill(state, blink_on, color_name)
        r = int(fill_hex[1:3], 16)
        g = int(fill_hex[3:5], 16)
        b = int(fill_hex[5:7], 16)
        draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(r, g, b))

    return img


def save_tray_icon_ico(output_path):
    """生成与托盘一致的多尺寸 .ico，供 Windows exe 打包使用（BMP 格式，兼容 PyInstaller）"""
    from PIL import Image

    base = render_traffic_icon("red", True).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    master = base.resize((256, 256), Image.Resampling.LANCZOS)
    master.save(
        output_path,
        format="ICO",
        sizes=[(size, size) for size in sizes],
        bitmap_format="bmp",
    )


def format_title(state, blink_on):
    """macOS 菜单栏文字显示"""
    lights = [LIGHT_OFF, LIGHT_OFF, LIGHT_OFF]
    if state == "green":
        lights[2] = LIGHT_ON["green"]
    elif state == "yellow":
        lights[1] = LIGHT_ON["yellow"] if blink_on else LIGHT_OFF
    else:
        lights[0] = LIGHT_ON["red"]
    return " ".join(lights)
