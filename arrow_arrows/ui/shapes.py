"""图形绘制工具：渐变 / 柔光 / 阴影、霓虹箭头、爱心星星等图标、文字排版。

这一层不关心游戏状态，只提供「画一个好看的东西」的能力，全部用 Pygame 的绘制指令
现场生成（项目里没有任何图片素材文件）。带 ``lru_cache`` 的都是在整个运行期只算一次的：
箭头图标、柔和阴影、径向柔光。
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Sequence, Tuple

import pygame

from . import theme

Color = Tuple[int, int, int]
Point = Tuple[float, float]

# ---------------------------------------------------------------------------- 背景与容器


def vertical_gradient(size: Tuple[int, int], top: Color, bottom: Color) -> pygame.Surface:
    """竖直线性渐变（背景用，生成一次即可）。"""
    width, height = size
    surface = pygame.Surface(size).convert()
    for y in range(height):
        t = y / max(1, height - 1)
        color = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))
    return surface


@lru_cache(maxsize=16)
def radial_glow(radius: int, color: Color, alpha: int) -> pygame.Surface:
    """径向柔光：先在小图上画一圈圈同心圆，再放大回去，就得到了柔和的光晕。"""
    small = pygame.Surface((32, 32), pygame.SRCALPHA)
    for i in range(16, 0, -1):
        t = i / 16.0
        a = int(alpha * (1.0 - t) ** 2)
        pygame.draw.circle(small, (*color, a), (16, 16), max(1, int(16 * t)))
    return pygame.transform.smoothscale(small, (radius * 2, radius * 2))


@lru_cache(maxsize=32)
def soft_shadow(size: Tuple[int, int], radius: int, spread: int, alpha: int) -> pygame.Surface:
    """柔和投影：同样用「小图画好再放大」的方式做出模糊边缘。"""
    small_w = max(4, size[0] // 8)
    small_h = max(4, size[1] // 8)
    small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    inset = max(1, spread // 8)
    pygame.draw.rect(small, (0, 0, 0, alpha), small.get_rect().inflate(-inset * 2, -inset * 2),
                     border_radius=max(2, radius // 8))
    return pygame.transform.smoothscale(small, size)


def drop_shadow(surface: pygame.Surface, rect: pygame.Rect, radius: int = 20, spread: int = 16,
                alpha: int = 120, offset: int = 6) -> None:
    """在 rect 下方垫一层柔和阴影（先画它，再画本体）。"""
    size = (rect.width + spread * 2, rect.height + spread * 2)
    shadow = soft_shadow(size, radius, spread, alpha)
    surface.blit(shadow, (rect.x - spread, rect.y - spread + offset))


def rounded_rect(
    surface: pygame.Surface,
    rect: pygame.Rect | Sequence[float],
    color: Color,
    radius: int = 14,
    width: int = 0,
) -> None:
    pygame.draw.rect(surface, color, pygame.Rect(rect), width, border_radius=int(radius))


def vertical_rounded_gradient(rect: pygame.Rect, radius: int, top: Color, bottom: Color) -> pygame.Surface:
    """给面板用的竖向渐变（画在小图上再放大，边缘用圆角遮罩裁一下）。"""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        color = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pygame.draw.line(layer, color, (0, y), (rect.width, y))
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return layer


def panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    radius: int = 24,
    top: Color = theme.PANEL_TOP,
    bottom: Color = theme.PANEL_BOTTOM,
    edge: Color = theme.PANEL_EDGE,
    shadow: bool = True,
) -> None:
    """一块带柔和阴影、竖向渐变和 1px 亮边的深色面板。"""
    if shadow:
        drop_shadow(surface, rect, radius=radius, spread=18, alpha=130, offset=8)
    surface.blit(vertical_rounded_gradient(rect, radius, top, bottom), rect.topleft)
    rounded_rect(surface, rect, edge, radius=radius, width=1)
    # 顶部一道极淡的高光，让面板有厚度
    gloss = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height // 3)
    layer = pygame.Surface(gloss.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (255, 255, 255, 10), layer.get_rect(), border_radius=radius - 2)
    surface.blit(layer, gloss.topleft)


def chip(surface: pygame.Surface, rect: pygame.Rect, radius: int = 17) -> None:
    """半透明小胶囊（用来装爱心、计时）。"""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, theme.CHIP_BG, layer.get_rect(), border_radius=radius)
    pygame.draw.rect(layer, theme.CHIP_EDGE, layer.get_rect(), width=1, border_radius=radius)
    surface.blit(layer, rect.topleft)


# ---------------------------------------------------------------------------- 文字


def text(
    surface: pygame.Surface,
    content: str,
    pos: Sequence[float],
    size: int = 20,
    bold: bool = False,
    color: Color = theme.TEXT,
    anchor: str = "center",
    shadow: bool = True,
    alpha: int = 255,
) -> pygame.Rect:
    """画一行文字；``anchor`` 支持 topleft / midtop / center / midleft / midright 等。"""
    font = theme.font(size, bold)
    image = font.render(content, True, color)
    if alpha < 255:
        image = image.copy()
        image.set_alpha(alpha)
    rect = image.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        shade = font.render(content, True, (6, 9, 24))
        if alpha < 255:
            shade = shade.copy()
            shade.set_alpha(alpha)
        surface.blit(shade, (rect.x + 1, rect.y + 2))
    surface.blit(image, rect)
    return rect


def text_tracked(
    surface: pygame.Surface,
    content: str,
    pos: Sequence[float],
    size: int = 12,
    color: Color = theme.TEXT_DIM,
    tracking: int = 3,
    bold: bool = False,
    anchor: str = "center",
) -> pygame.Rect:
    """带字距的文字（小号标签用，看起来更精致）。"""
    font = theme.font(size, bold)
    images = [font.render(char, True, color) for char in content]
    width = sum(image.get_width() for image in images) + tracking * max(0, len(images) - 1)
    height = font.get_height()
    rect = pygame.Rect(0, 0, width, height)
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    x = rect.x
    for image in images:
        surface.blit(image, (x, rect.y))
        x += image.get_width() + tracking
    return rect


def text_width(content: str, size: int, bold: bool = False) -> int:
    return theme.font(size, bold).size(content)[0]


# ---------------------------------------------------------------------------- 箭头


@lru_cache(maxsize=512)
def arrow_surface(size: int, direction_name: str, color: Color) -> pygame.Surface:
    """一枚霓虹箭头的贴图（朝上，其它方向靠旋转），带柔光、深色描边和高光。

    形状是「圆头短杆 + 三角箭头」，比实心大方块轻快得多，在深色棋盘上像发光的箭头。
    """
    pad = max(3, int(size * 0.42))
    side = int(size + pad * 2)
    surface = pygame.Surface((side, side), pygame.SRCALPHA)

    cx = side / 2.0
    cy = side / 2.0
    length = float(size)
    head_h = length * 0.42
    head_w = size * 0.76
    shaft_w = max(2.0, size * 0.26)
    tip_y = cy - length / 2.0
    base_y = tip_y + head_h
    tail_y = cy + length / 2.0

    dark = tuple(int(c * 0.32) for c in color)
    light = tuple(min(255, int(c + (255 - c) * 0.55)) for c in color)

    def paint(grow: float, fill) -> None:
        width = shaft_w + grow
        pygame.draw.line(surface, fill, (cx, base_y - 1), (cx, tail_y), int(round(width)))
        pygame.draw.circle(surface, fill, (int(cx), int(tail_y)), int(round(width / 2)))
        pygame.draw.polygon(surface, fill, [
            (cx, tip_y - grow * 0.5),
            (cx + head_w / 2 + grow, base_y),
            (cx - head_w / 2 - grow, base_y),
        ])

    # 由外到内叠：柔光 → 描边 → 本体 → 高光
    paint(6.0, (*color, 34))
    paint(3.0, (*color, 70))
    paint(1.6, (*dark, 255))
    paint(0.0, (*color, 255))
    pygame.draw.line(surface, (*light, 200),
                     (cx - shaft_w * 0.24, base_y), (cx - shaft_w * 0.24, tail_y - shaft_w * 0.45),
                     max(1, int(shaft_w * 0.3)))

    angle = {"UP": 0, "RIGHT": -90, "DOWN": 180, "LEFT": 90}[direction_name]
    if angle:
        surface = pygame.transform.rotate(surface, angle)
    return surface


def draw_arrow(
    surface: pygame.Surface,
    center: Point,
    size: float,
    direction_name: str,
    color: Color,
    scale: float = 1.0,
    alpha: int = 255,
) -> None:
    """在 ``center`` 处画一枚箭头图标。"""
    image = arrow_surface(int(round(size)), direction_name, color)
    if scale != 1.0:
        image = pygame.transform.smoothscale(
            image, (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
        )
    if alpha < 255:
        image = image.copy()
        image.set_alpha(alpha)
    surface.blit(image, image.get_rect(center=(int(center[0]), int(center[1]))))


# ---------------------------------------------------------------------------- 图标


def _heart_points(center: Point, size: float) -> List[Point]:
    cx, cy = center
    points: List[Point] = []
    for i in range(40):
        t = math.pi * 2 * i / 40
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x * size / 32.0, cy - y * size / 32.0))
    return points


def draw_heart(
    surface: pygame.Surface,
    center: Point,
    size: float,
    color: Color = theme.HEART,
    filled: bool = True,
    alpha: int = 255,
) -> None:
    points = _heart_points(center, size)
    if not filled:
        pygame.draw.polygon(surface, color, points, 2)
        return
    if alpha >= 255:
        glow = _heart_points(center, size * 1.25)
        layer = pygame.Surface((int(size * 3), int(size * 3)), pygame.SRCALPHA)
        local = _heart_points((size * 1.5, size * 1.5), size * 1.25)
        pygame.draw.polygon(layer, (*color, 46), local)
        surface.blit(layer, layer.get_rect(center=(int(center[0]), int(center[1]))))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, tuple(int(c * 0.62) for c in color), points, 2)
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(center[0] - size * 0.15), int(center[1] - size * 0.17)), max(1, int(size * 0.065)))
        return
    side = int(size * 2.6 + 8)
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    local_center = (side / 2, side / 2)
    pygame.draw.polygon(layer, (*color, alpha), _heart_points(local_center, size))
    pygame.draw.polygon(layer, (*tuple(int(c * 0.62) for c in color), alpha), _heart_points(local_center, size), 2)
    surface.blit(layer, layer.get_rect(center=(int(center[0]), int(center[1]))))


def draw_star(
    surface: pygame.Surface,
    center: Point,
    size: float,
    color: Color = theme.ACCENT,
    filled: bool = True,
    rotation: float = -math.pi / 2,
    width: int = 2,
    glow: bool = False,
) -> None:
    points: List[Point] = []
    for i in range(10):
        radius = size if i % 2 == 0 else size * 0.44
        angle = rotation + i * math.pi / 5
        points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
    if not filled:
        pygame.draw.polygon(surface, color, points, width)
        return
    if glow:
        side = int(size * 3)
        layer = pygame.Surface((side, side), pygame.SRCALPHA)
        local = [(x - center[0] + side / 2, y - center[1] + side / 2) for (x, y) in points]
        big = [(side / 2 + (x - side / 2) * 1.3, side / 2 + (y - side / 2) * 1.3) for (x, y) in local]
        pygame.draw.polygon(layer, (*color, 60), big)
        surface.blit(layer, layer.get_rect(center=(int(center[0]), int(center[1]))))
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, tuple(int(c * 0.7) for c in color), points, max(1, width - 1))


def draw_pause_icon(surface: pygame.Surface, center: Point, size: float, color: Color = theme.TEXT_MUTED) -> None:
    """暂停图标：两根圆角竖条。"""
    bar_w = max(3, int(size * 0.24))
    bar_h = max(6, int(size * 1.0))
    gap = max(2, int(size * 0.22))
    for sign in (-1, 1):
        rect = pygame.Rect(0, 0, bar_w, bar_h)
        rect.center = (int(center[0] + sign * (bar_w / 2 + gap / 2)), int(center[1]))
        pygame.draw.rect(surface, color, rect, border_radius=bar_w // 2)


def draw_clock(surface: pygame.Surface, center: Point, size: float, color: Color = theme.TEXT_MUTED) -> None:
    cx, cy = center
    pygame.draw.circle(surface, color, (int(cx), int(cy)), int(size * 0.52), max(2, int(size * 0.13)))
    pygame.draw.line(surface, color, (cx, cy), (cx, cy - size * 0.3), max(2, int(size * 0.13)))
    pygame.draw.line(surface, color, (cx, cy), (cx + size * 0.24, cy + size * 0.09), max(2, int(size * 0.13)))


def draw_lock(surface: pygame.Surface, center: Point, size: float, color: Color = theme.TEXT_DIM) -> None:
    cx, cy = center
    body = pygame.Rect(0, 0, size * 1.05, size * 0.8)
    body.center = (int(cx), int(cy + size * 0.26))
    rounded_rect(surface, body, color, radius=int(size * 0.18))
    pygame.draw.arc(surface, color,
                    pygame.Rect(int(cx - size * 0.36), int(cy - size * 0.7), int(size * 0.72), int(size * 0.86)),
                    math.pi, math.pi * 2, max(2, int(size * 0.15)))


def ring(surface: pygame.Surface, center: Point, radius: float, color: Color, width: int = 3,
         alpha: int = 255) -> None:
    """半透明圆环（悬停 / 提示高亮用）。"""
    if alpha >= 255:
        pygame.draw.circle(surface, color, (int(center[0]), int(center[1])), int(radius), width)
        return
    side = int(radius * 2 + 10)
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    pygame.draw.circle(layer, (*color, alpha), (side // 2, side // 2), int(radius), width)
    surface.blit(layer, layer.get_rect(center=(int(center[0]), int(center[1]))))


def dot(surface: pygame.Surface, center: Point, radius: float, color: Color, alpha: int = 255) -> None:
    if alpha >= 255:
        pygame.draw.circle(surface, color, (int(center[0]), int(center[1])), max(1, int(radius)))
        return
    side = int(radius * 2 + 6)
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    pygame.draw.circle(layer, (*color, alpha), (side // 2, side // 2), max(1, int(radius)))
    surface.blit(layer, layer.get_rect(center=(int(center[0]), int(center[1]))))


def dashed_line(
    surface: pygame.Surface,
    start: Point,
    end: Point,
    color: Color,
    width: int = 3,
    dash: int = 7,
    alpha: int = 255,
) -> None:
    """虚线（画箭头弹道预览用）。"""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return
    ux, uy = dx / length, dy / length
    layer = surface
    offset = (0, 0)
    if alpha < 255:
        pad = 6
        layer = pygame.Surface((int(abs(dx)) + pad * 2, int(abs(dy)) + pad * 2), pygame.SRCALPHA)
        offset = (min(start[0], end[0]) - pad, min(start[1], end[1]) - pad)
    travelled = 0.0
    while travelled < length:
        seg = min(dash, length - travelled)
        p1 = (start[0] + ux * travelled - offset[0], start[1] + uy * travelled - offset[1])
        p2 = (start[0] + ux * (travelled + seg) - offset[0], start[1] + uy * (travelled + seg) - offset[1])
        pygame.draw.line(layer, color, p1, p2, width)
        travelled += dash * 1.9
    if alpha < 255:
        layer.set_alpha(alpha)
        surface.blit(layer, offset)
