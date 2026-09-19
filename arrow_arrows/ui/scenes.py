"""场景绘制：主菜单、选关、玩法说明、游戏界面，以及暂停 / 过关 / 失败弹层。

每个 ``draw_*`` 都返回本帧可点击的按钮列表，App 直接拿它做命中判定——
绘制和可点击区域永远是同一份数据，不会出现「按钮画在这里、能点的地方在那里」。
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import pygame

from . import shapes, theme, widgets
from .widgets import Button

Color = Tuple[int, int, int]

LEVEL_COLUMNS = 5
LEVEL_ROWS = 6


# ---------------------------------------------------------------------------- 小工具


def format_time(seconds: float) -> str:
    """把秒数格式化成原游戏那种 ``6m38s``。"""
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def wrap_text(content: str, size: int, max_width: int, bold: bool = False) -> List[str]:
    """按像素宽度折行（中文没有空格，所以逐字累加宽度）。"""
    font = theme.font(size, bold)
    lines: List[str] = []
    current = ""
    for char in content:
        probe = current + char
        if font.size(probe)[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = probe
    if current:
        lines.append(current)
    return lines


def draw_background(surface: pygame.Surface, app) -> None:
    """背景是一张预渲染好的图（渐变 + 两处柔光），每帧只 blit 一次。"""
    surface.blit(app.backdrop, (0, 0))


def draw_scrim(surface: pygame.Surface, alpha: int = 168) -> None:
    layer = pygame.Surface((theme.LOGICAL_W, theme.LOGICAL_H), pygame.SRCALPHA)
    layer.fill((*theme.SCRIM, alpha))
    surface.blit(layer, (0, 0))


def draw_card(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """弹层用的卡片（比棋盘面板亮一点，弹出来才有存在感）。"""
    shapes.panel(surface, rect, radius=28, top=(48, 65, 130), bottom=(25, 34, 74), shadow=True)


def draw_title(surface: pygame.Surface, center_x: float, y: float, label: str, value: str) -> None:
    """顶部标题：上面一行小字标签，下面一行大字。"""
    shapes.text_tracked(surface, label, (center_x, y), 12, theme.TEXT_DIM, tracking=4)
    shapes.text(surface, value, (center_x, y + 24), 34, True, theme.TEXT)


def draw_stat_chips(surface: pygame.Surface, app) -> None:
    """两枚小胶囊：剩余机会（爱心）与计时。"""
    label = "剩余机会"
    label_w = shapes.text_width(label, 14)
    hearts_w = app.max_lives * 21
    chip1_w = 14 + label_w + 10 + hearts_w + 14
    time_text = format_time(app.elapsed)
    time_w = shapes.text_width(time_text, 16, True)
    chip2_w = 18 + 16 + 8 + time_w + 16
    gap = 12
    total = chip1_w + gap + chip2_w
    x = (theme.LOGICAL_W - total) / 2
    y = theme.CHIP_Y

    chip1 = pygame.Rect(int(x), int(y - 17), int(chip1_w), 34)
    shapes.chip(surface, chip1, 17)
    shapes.text(surface, label, (chip1.x + 14, chip1.centery), 14, False, theme.TEXT_MUTED,
                anchor="midleft", shadow=False)
    hearts_x = chip1.x + 14 + label_w + 10 + 10
    for index in range(app.max_lives):
        filled = index < app.lives
        shapes.draw_heart(surface, (hearts_x + index * 21, chip1.centery), 19,
                          theme.HEART if filled else theme.HEART_EMPTY,
                          filled=filled, alpha=255 if filled else 170)

    chip2 = pygame.Rect(int(x + chip1_w + gap), int(y - 17), int(chip2_w), 34)
    shapes.chip(surface, chip2, 17)
    shapes.draw_clock(surface, (chip2.x + 19, chip2.centery), 16, theme.TEXT_MUTED)
    shapes.text(surface, time_text, (chip2.x + 34, chip2.centery), 16, True, theme.TEXT,
                anchor="midleft", shadow=False)


def draw_progress(surface: pygame.Surface, app) -> None:
    """棋盘面板底部的「剩余箭头」进度条。"""
    total = max(1, app.total_arrows)
    remaining = app.board.arrow_count if app.board else 0
    ratio = 1.0 - remaining / total
    bar = theme.PROGRESS_BAR
    shapes.rounded_rect(surface, bar, (10, 16, 40), radius=bar.height // 2)
    if ratio > 0:
        width = max(bar.height, int(bar.width * ratio))
        fill = pygame.Rect(bar.x, bar.y, width, bar.height)
        layer = pygame.Surface(fill.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (255, 255, 255, 255), layer.get_rect(), border_radius=bar.height // 2)
        surface.blit(layer, fill.topleft, special_flags=pygame.BLEND_RGBA_MIN)
        shapes.rounded_rect(surface, fill, theme.GOOD, radius=bar.height // 2)
    shapes.rounded_rect(surface, bar, (255, 255, 255, 22), radius=bar.height // 2, width=1)
    shapes.text(surface, f"剩余箭头 {remaining} / {total}",
                (theme.PROGRESS_LABEL_X, bar.centery), 15, False, theme.TEXT_MUTED,
                anchor="midleft", shadow=False)


# ---------------------------------------------------------------------------- 主菜单


def draw_menu(surface: pygame.Surface, app) -> List[Button]:
    draw_background(surface, app)

    shapes.text(surface, "一箭又一箭", (theme.LOGICAL_W / 2, 196), 52, True, theme.TEXT)
    shapes.text_tracked(surface, "ARROW  ·  ONE  BY  ONE", (theme.LOGICAL_W / 2, 246), 13,
                        theme.TEXT_DIM, tracking=3)

    buttons = [
        Button(pygame.Rect(90, 322, 300, 60), "开始游戏", "start", size=25, style="gold"),
        Button(pygame.Rect(90, 396, 300, 56), f"选择关卡  ·  {app.progress.unlocked}/{app.total_levels}",
               "levels", size=20),
        Button(pygame.Rect(90, 466, 300, 56), "玩法说明", "help", size=20, style="ghost"),
        Button(pygame.Rect(90, 536, 300, 56), "退出游戏", "quit", size=20, style="ghost"),
    ]
    for button in buttons:
        button.draw(surface, app.mouse_logical, app.pressed == button.key)

    shapes.draw_star(surface, (196, 634), 11, theme.ACCENT, filled=True, glow=True)
    shapes.text(surface, f"已获得 {app.progress.total_stars()} 颗星 / 共 {app.total_levels * 3} 颗",
                (218, 634), 17, False, theme.TEXT_MUTED, anchor="midleft", shadow=False)

    demo = ["UP", "RIGHT", "DOWN", "LEFT", "UP"]
    for index, direction in enumerate(demo):
        shapes.draw_arrow(surface, (120 + index * 60, 686), 40, direction,
                          theme.arrow_color(index + 1))

    shapes.text(surface, "30 关全部随机生成 · 每一关都保证可解", (theme.LOGICAL_W / 2, 742), 14,
                False, theme.TEXT_DIM, shadow=False)
    return buttons


# ---------------------------------------------------------------------------- 选关


def draw_level_select(surface: pygame.Surface, app) -> List[Button]:
    draw_background(surface, app)
    shapes.text(surface, "选择关卡", (theme.LOGICAL_W / 2, 62), 30, True, theme.TEXT)
    shapes.text(surface, f"已解锁 {app.progress.unlocked} 关  ·  拿到 {app.progress.total_stars()} 颗星",
                (theme.LOGICAL_W / 2, 98), 15, False, theme.TEXT_MUTED, shadow=False)

    buttons: List[Button] = []
    size = 72
    gap_x, gap_y = 12, 14
    total_w = LEVEL_COLUMNS * size + (LEVEL_COLUMNS - 1) * gap_x
    start_x = (theme.LOGICAL_W - total_w) / 2
    start_y = 134
    for index in range(app.total_levels):
        row, column = divmod(index, LEVEL_COLUMNS)
        rect = pygame.Rect(int(start_x + column * (size + gap_x)), start_y + row * (size + gap_y), size, size)
        level = index + 1
        button = Button(rect, str(level), f"level:{level}", style="level",
                        locked=not app.progress.is_unlocked(level),
                        badge=app.progress.stars_of(level))
        button.draw(surface, app.mouse_logical, app.pressed == button.key)
        buttons.append(button)

    back = Button(pygame.Rect(140, 748, 200, 52), "返回主菜单", "menu", size=20, style="ghost")
    back.draw(surface, app.mouse_logical, app.pressed == back.key)
    buttons.append(back)
    return buttons


# ---------------------------------------------------------------------------- 玩法说明


HELP_LINES: Sequence[Tuple[str, str]] = (
    ("目标", "把所有箭头都射出棋盘，清空即过关。"),
    ("操作", "鼠标左键点一个箭头，它会朝箭头所指的方向飞出去。"),
    ("规则", "箭头正前方到棋盘边缘整条线都是空的（没有别的箭头、没有墙）时，它才飞得出去。"),
    ("反馈", "点中被挡住的箭头会抖动、闪红，并扣掉一次机会；三次机会用完本关失败。"),
    ("技巧", "鼠标悬停在箭头上会出现弹道预览：绿色表示能飞，红色会把拦路的箭头圈出来。"),
    ("提示", "按 H 或点「提示」按钮，会高亮一个当前可以点的箭头。"),
    ("不会卡死", "点掉一个箭头只会让别的箭头更好飞，绝不会把局面弄得更糟。"),
    ("快捷键", "R 重开本关 · N 换一局 · H 提示 · M 静音 · Esc 暂停 / 返回"),
)


def draw_help(surface: pygame.Surface, app) -> List[Button]:
    draw_background(surface, app)
    shapes.text(surface, "玩法说明", (theme.LOGICAL_W / 2, 58), 30, True, theme.TEXT)

    card = pygame.Rect(24, 100, 432, 560)
    draw_card(surface, card)

    y = 130
    for title, content in HELP_LINES:
        shapes.rounded_rect(surface, pygame.Rect(48, y + 3, 3, 18), theme.ACCENT, radius=2)
        shapes.text(surface, title, (60, y + 11), 18, True, theme.ACCENT, anchor="midleft", shadow=False)
        lines = wrap_text(content, 16, 366)
        y += 26
        for line in lines:
            shapes.text(surface, line, (60, y), 16, False, theme.TEXT, anchor="topleft", shadow=False)
            y += 23
        y += 10

    back = Button(pygame.Rect(140, 692, 200, 52), "返回", "menu", size=20, style="gold")
    back.draw(surface, app.mouse_logical, app.pressed == back.key)
    return [back]


# ---------------------------------------------------------------------------- 游戏界面


def draw_game(surface: pygame.Surface, app) -> List[Button]:
    draw_background(surface, app)

    # 顶部：暂停按钮 + 关卡号
    pause = Button(theme.PAUSE_BTN, "", "pause", style="invisible")
    shapes.chip(surface, theme.PAUSE_BTN, 14)
    shapes.draw_pause_icon(surface, theme.PAUSE_BTN.center, 11, theme.TEXT_MUTED)
    draw_title(surface, theme.LOGICAL_W / 2, theme.TITLE_LABEL_Y, "关卡", str(app.level))
    if app.level >= 5:
        shapes.draw_star(surface, (418, 42), 8, (120, 146, 232), filled=True)
        shapes.draw_star(surface, (442, 62), 6, (100, 122, 200), filled=True)

    draw_stat_chips(surface, app)

    # 棋盘
    app.view.draw(surface)
    draw_progress(surface, app)

    # 底部按钮
    row = widgets.button_row(theme.BUTTON_ROW_Y, [("重开 (R)", "restart"), ("提示 (H)", "hint"),
                                                  ("菜单 (Esc)", "pause")],
                             height=theme.BUTTON_ROW_H, width=136, gap=14, start_x=22, size=18)
    buttons: List[Button] = [pause]
    for button in row:
        button.enabled = not (button.key == "restart" and app.pending_win > 0)
        button.draw(surface, app.mouse_logical, app.pressed == button.key)
        buttons.append(button)

    # 悬停说明（画在按钮之后，避免被压住）
    if app.hover_text:
        color = theme.GOOD if app.hover_free else theme.DANGER
        width = shapes.text_width(app.hover_text, 17, True)
        pill = pygame.Rect(0, 0, width + 28, 32)
        pill.center = (theme.LOGICAL_W // 2, theme.HOVER_TEXT_Y)
        layer = pygame.Surface(pill.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (10, 14, 34, 225), layer.get_rect(), border_radius=16)
        pygame.draw.rect(layer, (*color, 210), layer.get_rect(), width=1, border_radius=16)
        surface.blit(layer, pill.topleft)
        shapes.text(surface, app.hover_text, pill.center, 17, True, color, shadow=False)

    shapes.text(surface, "点击箭头让它飞出去 · 前方全空才能飞", (theme.LOGICAL_W / 2, theme.TIPS_Y),
                15, False, theme.TEXT_DIM, shadow=False)
    return buttons


# ---------------------------------------------------------------------------- 弹层


def draw_pause(surface: pygame.Surface, app) -> List[Button]:
    draw_scrim(surface)
    card = pygame.Rect(48, 268, 384, 300)
    draw_card(surface, card)
    shapes.text(surface, "已暂停", (card.centerx, card.y + 56), 32, True, theme.TEXT)
    shapes.text(surface, f"第 {app.level} 关 · 用时 {format_time(app.elapsed)} · 失误 {app.mistakes} 次",
                (card.centerx, card.y + 98), 16, False, theme.TEXT_MUTED, shadow=False)
    if app.audio.muted:
        shapes.text(surface, "音效已静音（按 M 恢复）", (card.centerx, card.y + 124), 14, False,
                    theme.TEXT_DIM, shadow=False)

    row1 = widgets.button_row(card.y + 152, [("继续", "resume"), ("重开本关", "restart")],
                              height=50, width=158, gap=16, start_x=card.x + 26, size=19)
    row1[0].style = "gold"
    row2 = widgets.button_row(card.y + 216, [("换一局", "relayout"), ("返回主菜单", "menu")],
                              height=50, width=158, gap=16, start_x=card.x + 26, size=19,
                              style="ghost")
    buttons = row1 + row2
    for button in buttons:
        button.draw(surface, app.mouse_logical, app.pressed == button.key)
    return buttons


def draw_win(surface: pygame.Surface, app) -> List[Button]:
    draw_scrim(surface)
    card = pygame.Rect(40, 214, 400, 424)
    draw_card(surface, card)

    all_clear = app.level >= app.total_levels
    shapes.text(surface, "全部通关！" if all_clear else "过关！", (card.centerx, card.y + 56), 34, True,
                theme.ACCENT)

    for index in range(3):
        earned = index < app.stars
        appear = min(1.0, max(0.0, (app.overlay_t - 0.18 * index) / 0.22))
        if appear <= 0:
            continue
        pop = 1.0 + 0.45 * math.sin(appear * math.pi)
        center = (card.centerx + (index - 1) * 62, card.y + 132)
        shapes.draw_star(surface, center, (26 if earned else 24) * pop,
                         theme.ACCENT if earned else (58, 70, 112), filled=True, glow=earned)

    stats = [("用时", format_time(app.elapsed)), ("失误", f"{app.mistakes} 次"),
             ("提示", f"{app.hints_used} 次")]
    best = app.progress.best_time.get(app.level)
    if best is not None:
        stats.append(("最好成绩", format_time(best)))
    top = card.y + 190
    for index, (label, value) in enumerate(stats):
        y = top + index * 31
        shapes.text(surface, label, (card.centerx - 16, y), 17, False, theme.TEXT_MUTED,
                    anchor="midright", shadow=False)
        shapes.text(surface, value, (card.centerx + 16, y), 17, True, theme.TEXT,
                    anchor="midleft", shadow=False)

    if all_clear:
        row = widgets.button_row(card.bottom - 78, [("再玩一次", "restart"), ("选关", "levels")],
                                 height=50, width=158, gap=16, start_x=card.x + 26, size=19)
        row[0].style = "gold"
    else:
        row = widgets.button_row(card.bottom - 78, [("下一关", "next"), ("重玩", "restart"), ("选关", "levels")],
                                 height=50, width=110, gap=14, start_x=card.x + 20, size=18)
        row[0].style = "gold"
    for button in row:
        button.draw(surface, app.mouse_logical, app.pressed == button.key)
    return list(row)


def draw_lose(surface: pygame.Surface, app) -> List[Button]:
    draw_scrim(surface)
    card = pygame.Rect(48, 272, 384, 292)
    draw_card(surface, card)
    shapes.text(surface, "机会用完了", (card.centerx, card.y + 58), 32, True, theme.DANGER)
    shapes.text(surface, f"第 {app.level} 关还剩 {app.board.arrow_count} 个箭头",
                (card.centerx, card.y + 102), 18, False, theme.TEXT, shadow=False)
    shapes.text(surface, "小技巧：把鼠标移到箭头上，先看弹道再点", (card.centerx, card.y + 132),
                15, False, theme.TEXT_DIM, shadow=False)

    row1 = widgets.button_row(card.y + 168, [("再来一次", "restart"), ("换一局", "relayout")],
                              height=52, width=158, gap=16, start_x=card.x + 26, size=19)
    row1[0].style = "gold"
    row2 = widgets.button_row(card.y + 232, [("返回主菜单", "menu")],
                              height=48, width=200, gap=16, start_x=card.x + 92, size=18, style="ghost")
    buttons = row1 + row2
    for button in buttons:
        button.draw(surface, app.mouse_logical, app.pressed == button.key)
    return buttons
