"""按钮控件：预渲染的渐变底 + 阴影 + 悬停/按下反馈，以及关卡格子样式。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pygame

from . import shapes, theme

Color = Tuple[int, int, int]

# 每种风格：(主体色, 顶部亮色, 描边色)
_STYLES: Dict[str, Tuple[Color, Color, Color]] = {
    "primary": (theme.BTN, theme.BTN_TOP, theme.BTN_EDGE),
    "gold": (theme.BTN_GOLD, theme.BTN_GOLD_TOP, theme.BTN_GOLD_EDGE),
    "danger": (theme.BTN_DANGER, theme.BTN_DANGER_TOP, theme.BTN_DANGER_EDGE),
    "ghost": (theme.BTN_GHOST, theme.BTN_GHOST_TOP, theme.BTN_GHOST_EDGE),
    "disabled": (theme.BTN_DISABLED, theme.BTN_DISABLED, theme.PANEL_EDGE),
}


@lru_cache(maxsize=96)
def button_face(size: Tuple[int, int], style: str, radius: int = 16) -> pygame.Surface:
    """按钮底：竖向渐变 + 1px 亮边 + 顶部一抹高光。缓存起来避免每帧重画。"""
    base, top, edge = _STYLES.get(style, _STYLES["primary"])
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        # 上半部分更亮，下半部分压回主体色，形成柔和的立体感
        k = (1.0 - t) ** 1.4
        color = (
            int(base[0] + (top[0] - base[0]) * k),
            int(base[1] + (top[1] - base[1]) * k),
            int(base[2] + (top[2] - base[2]) * k),
        )
        pygame.draw.line(surface, color, (0, y), (rect.width, y))
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(surface, edge, rect, width=1, border_radius=radius)
    gloss = pygame.Rect(2, 2, rect.width - 4, max(3, rect.height // 3))
    layer = pygame.Surface(gloss.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (255, 255, 255, 22), layer.get_rect(), border_radius=max(2, radius - 2))
    surface.blit(layer, gloss.topleft)
    return surface


@lru_cache(maxsize=24)
def level_face(size: int, radius: int = 18) -> pygame.Surface:
    """关卡格子底：比按钮更方，渐变更淡。"""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = surface.get_rect()
    for y in range(size):
        t = y / max(1, size - 1)
        color = (int(44 + (70 - 44) * (1 - t)), int(60 + (98 - 60) * (1 - t)),
                 int(126 + (186 - 126) * (1 - t)))
        pygame.draw.line(surface, color, (0, y), (size, y))
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(surface, theme.BTN_EDGE, rect, width=1, border_radius=radius)
    return surface


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    key: str
    size: int = 20
    style: str = "primary"
    enabled: bool = True
    badge: int = 0          # 关卡格子：已获得的星星数
    locked: bool = False    # 关卡格子：是否未解锁
    text_color: Optional[Color] = None
    glow: float = 0.0       # 外部传入的呼吸光效强度（0~1）

    def hit(self, pos: Tuple[float, float]) -> bool:
        return self.enabled and self.rect.collidepoint(pos)

    # ------------------------------------------------------------------ 绘制

    def draw(self, surface: pygame.Surface, mouse: Tuple[float, float], pressed: bool = False) -> None:
        if self.style == "invisible":
            return
        if self.style == "level":
            self._draw_level(surface, mouse)
            return

        hovered = self.hit(mouse) and not self.locked
        style = self.style if self.enabled else "disabled"
        rect = self.rect.move(0, 2 if pressed else 0)
        if not pressed:
            shapes.drop_shadow(surface, rect, radius=16, spread=10, alpha=120, offset=5)
        surface.blit(button_face(rect.size, style, 16), rect.topleft)
        if hovered:
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (255, 255, 255, 26), layer.get_rect(), border_radius=16)
            surface.blit(layer, rect.topleft)
        if self.glow > 0:
            shapes.ring(surface, rect.center, rect.width / 2 + 5, theme.ACCENT, 2, int(130 * self.glow))
        color = self.text_color or (theme.BTN_TEXT if self.enabled else theme.TEXT_DIM)
        shapes.text(surface, self.label, rect.center, self.size, True, color)

    def _draw_level(self, surface: pygame.Surface, mouse: Tuple[float, float]) -> None:
        hovered = self.hit(mouse) and not self.locked
        rect = self.rect
        if not self.locked:
            shapes.drop_shadow(surface, rect, radius=18, spread=10, alpha=110, offset=5)
            if hovered:
                face = level_face(rect.width + 6, 18)
                surface.blit(face, (rect.x - 3, rect.y - 3))
            surface.blit(level_face(rect.width, 18), rect.topleft)
            if hovered:
                shapes.rounded_rect(surface, rect, (255, 255, 255), radius=18, width=2)
            shapes.text(surface, self.label, (rect.centerx, rect.centery - 7), 26, True, theme.TEXT)
            for i in range(3):
                filled = i < self.badge
                shapes.draw_star(
                    surface,
                    (rect.centerx + (i - 1) * 16, rect.bottom - 15),
                    7,
                    theme.ACCENT if filled else (66, 78, 120),
                    filled=filled,
                    width=1,
                )
            return
        # 未解锁
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (20, 27, 56, 235), layer.get_rect(), border_radius=18)
        surface.blit(layer, rect.topleft)
        shapes.rounded_rect(surface, rect, (60, 74, 118), radius=18, width=1)
        shapes.draw_lock(surface, (rect.centerx, rect.centery - 2), 17, (116, 132, 182))


def button_row(
    y: int,
    specs: List[Tuple[str, str]],
    height: int = 50,
    width: int = 136,
    gap: int = 14,
    start_x: int = 22,
    size: int = 19,
    style: str = "primary",
) -> List[Button]:
    """横向排一排按钮：``specs`` 是 (文案, key) 列表。"""
    buttons: List[Button] = []
    for index, (label, key) in enumerate(specs):
        rect = pygame.Rect(start_x + index * (width + gap), y, width, height)
        buttons.append(Button(rect, label, key, size=size, style=style))
    return buttons
