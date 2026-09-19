"""主题：配色、字体、布局常量。

整体走「深空靛蓝底 + 霓虹箭头」的干净风格：背景是几乎无花纹的深色渐变，
棋盘是一块带柔和阴影和微弱内发光的深色面板，箭头是高饱和度的霓虹色，
交互元素（按钮、进度、选中态）统一用琥珀色点缀。刻意不做斜条纹、
不做格子底块，让棋盘尽量清爽。
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

import pygame

# ---------------------------------------------------------------------------- 尺寸

LOGICAL_W, LOGICAL_H = 480, 854   # 逻辑分辨率（竖屏手机比例），窗口缩放时按它等比拉伸
FPS = 60

# ---------------------------------------------------------------------------- 配色

BG_TOP = (28, 38, 84)
BG_BOTTOM = (8, 11, 27)
GLOW = (78, 112, 236)

PANEL_TOP = (26, 37, 82)
PANEL_BOTTOM = (13, 19, 44)
PANEL_EDGE = (72, 96, 172)
PANEL_INNER = (11, 16, 38)
GRID_DOT = (58, 76, 134)

TILE_HOVER = (44, 64, 136)
TILE_HOVER_EDGE = (124, 156, 246)

WALL = (58, 74, 132)
WALL_EDGE = (92, 114, 180)

TEXT = (238, 243, 255)
TEXT_MUTED = (142, 158, 202)
TEXT_DIM = (104, 120, 168)

ACCENT = (255, 199, 89)
ACCENT_DEEP = (232, 158, 40)
GOOD = (86, 230, 160)
DANGER = (255, 92, 112)
HEART = (255, 86, 118)
HEART_EMPTY = (72, 56, 96)

CHIP_BG = (255, 255, 255, 16)
CHIP_EDGE = (255, 255, 255, 30)

BTN = (52, 74, 168)
BTN_TOP = (86, 116, 224)
BTN_EDGE = (118, 148, 240)
BTN_TEXT = (244, 248, 255)
BTN_SHADOW = (4, 6, 18)
BTN_DISABLED = (44, 52, 84)

BTN_GOLD = (238, 168, 52)
BTN_GOLD_TOP = (255, 206, 96)
BTN_GOLD_EDGE = (255, 228, 152)

BTN_DANGER = (196, 58, 84)
BTN_DANGER_TOP = (232, 92, 118)
BTN_DANGER_EDGE = (255, 148, 166)

BTN_GHOST = (30, 40, 82)
BTN_GHOST_TOP = (44, 58, 112)
BTN_GHOST_EDGE = (78, 96, 158)

SCRIM = (6, 8, 22)

ARROW_COLORS: List[Tuple[int, int, int]] = [
    (72, 228, 158),    # 薄荷绿
    (86, 176, 255),    # 天蓝
    (255, 110, 162),   # 桃粉
    (170, 134, 255),   # 紫罗兰
    (255, 178, 74),    # 琥珀
    (80, 236, 220),    # 青绿
    (255, 214, 96),    # 明黄
    (132, 152, 255),   # 靛蓝
    (255, 124, 96),    # 珊瑚
]

# ---------------------------------------------------------------------------- 布局

PAUSE_BTN = pygame.Rect(24, 26, 40, 40)
TITLE_LABEL_Y = 30
TITLE_Y = 54
CHIP_Y = 106
BOARD_PANEL = pygame.Rect(16, 140, 448, 500)
PROGRESS_BAR = pygame.Rect(44, 616, 296, 8)
PROGRESS_LABEL_X = 348
HOVER_TEXT_Y = 666
BUTTON_ROW_Y = 694
BUTTON_ROW_H = 50
TIPS_Y = 766

# ---------------------------------------------------------------------------- 字体

_FONT_CANDIDATES: List[str] = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

_font_path_cache: Dict[bool, str] = {}
_font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}


def _find_font_path(bold: bool) -> str:
    """找一个能显示中文的系统字体；找不到就退回 pygame 默认字体。"""
    if bold not in _font_path_cache:
        path = ""
        for candidate in _FONT_CANDIDATES:
            if os.path.exists(candidate):
                path = candidate
                break
        _font_path_cache[bold] = path
    return _font_path_cache[bold]


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """按字号取字体（带缓存）。"""
    key = (int(size), bool(bold))
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    path = _find_font_path(bold)
    if path:
        f = pygame.font.Font(path, key[0])
        # msyh.ttc 只有常规字重，加粗时用伪粗体补一下
        if bold and "msyhbd" not in path.lower():
            f.set_bold(True)
    else:
        f = pygame.font.SysFont("microsoftyahei,simhei,arial", key[0], bold=bold)
    _font_cache[key] = f
    return f


def arrow_color(index: int) -> Tuple[int, int, int]:
    return ARROW_COLORS[index % len(ARROW_COLORS)]


def arrow_dark(index: int, factor: float = 0.42) -> Tuple[int, int, int]:
    """箭头描边色：主色压暗。"""
    color = arrow_color(index)
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))
