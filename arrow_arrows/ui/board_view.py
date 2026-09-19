"""棋盘视图：坐标换算、棋盘绘制、以及全部动画表现。

这一层只管「怎么画」和「画动画」，不碰规则；规则判定全部来自 ``core``。
App 负责把一次点击拆成「规则结果 → 这里派生的动画」。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from ..core.model import Board, Cell, Direction
from . import shapes, theme

Color = Tuple[int, int, int]
Point = Tuple[float, float]


@dataclass
class FlyingArrow:
    """已经飞出棋盘、正在播放动画的箭头。"""

    head: Cell
    direction: Direction
    color: int
    start: Point
    offset: Point
    duration: float = 0.34
    elapsed: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)

    def position(self, factor: float) -> Point:
        return (self.start[0] + self.offset[0] * factor, self.start[1] + self.offset[1] * factor)


@dataclass
class Toast:
    """飘字提示。"""

    text: str
    color: Color
    pos: Point
    ttl: float = 1.1
    elapsed: float = 0.0


@dataclass
class Mark:
    """撞击 / 弹道残影标记。"""

    cell: Cell
    color: Color
    kind: str = "dot"          # dot / ring / wall
    ttl: float = 0.45
    elapsed: float = 0.0


class BoardView:
    """棋盘面板的绘制与动画状态机。"""

    def __init__(self, panel: pygame.Rect) -> None:
        self.panel = panel
        self.board: Optional[Board] = None
        self.level = 1
        self.cell = 40.0
        self.origin: Point = (0.0, 0.0)
        self.time = 0.0
        self.flying: List[FlyingArrow] = []
        self.toasts: List[Toast] = []
        self.marks: List[Mark] = []
        self.nudge: Optional[Tuple[Cell, float]] = None
        self.shake = 0.0
        self.shake_total = 0.36
        self.flash = 0.0
        self.spawn = 0.0
        self.spawn_total = 0.42
        self.hover = None
        self.hint_cell: Optional[Cell] = None
        self.hint_elapsed = 0.0
        self.hint_ttl = 2.6

    # ------------------------------------------------------------------ 布局

    def set_board(self, board: Board, level: int) -> None:
        self.board = board
        self.level = level
        self.flying.clear()
        self.toasts.clear()
        self.marks.clear()
        self.nudge = None
        self.shake = 0.0
        self.flash = 0.0
        self.spawn = self.spawn_total
        self.hover = None
        self.hint_cell = None
        self.hint_elapsed = 0.0
        self.layout()

    def layout(self) -> None:
        if self.board is None:
            return
        # 底部要给「剩余箭头」进度条留出位置，所以棋盘区域比面板略高一点收
        inner = pygame.Rect(self.panel.x + 18, self.panel.y + 16,
                            self.panel.width - 36, self.panel.height - 64)
        self.cell = min(inner.width / self.board.width, inner.height / self.board.height)
        width = self.cell * self.board.width
        height = self.cell * self.board.height
        self.origin = (inner.x + (inner.width - width) / 2, inner.y + (inner.height - height) / 2)

    def cell_center(self, x: int, y: int) -> Point:
        return (self.origin[0] + (x + 0.5) * self.cell, self.origin[1] + (y + 0.5) * self.cell)

    def px_to_cell(self, pos: Point) -> Optional[Cell]:
        if self.board is None:
            return None
        dx, dy = self.shake_offset()
        x = int((pos[0] - dx - self.origin[0]) // self.cell)
        y = int((pos[1] - dy - self.origin[1]) // self.cell)
        if 0 <= x < self.board.width and 0 <= y < self.board.height:
            return (x, y)
        return None

    def shake_offset(self) -> Point:
        if self.shake <= 0:
            return (0.0, 0.0)
        k = self.shake / self.shake_total
        amp = 7.0 * k
        return (math.sin(self.time * 63) * amp, math.cos(self.time * 47) * amp * 0.55)

    # ------------------------------------------------------------------ 动画触发

    def spawn_flying(self, arrow) -> None:
        start = self.cell_center(*arrow.head)
        steps = self.board.exit_steps(arrow) + 2.0
        offset = (arrow.direction.dx * steps * self.cell, arrow.direction.dy * steps * self.cell)
        self.flying.append(FlyingArrow(arrow.head, arrow.direction, arrow.color, start, offset))

    def spawn_blocked(self, result) -> None:
        """被挡住：棋盘抖一下、弹道闪红、拦路的箭头被圈出来、飘一行字。"""
        self.shake = self.shake_total
        self.flash = 0.4
        self.nudge = (result.arrow.cell, 0.34)
        for cell in result.open_cells:
            self.marks.append(Mark(cell, theme.DANGER, "dot", 0.45))
        if result.blocker is not None:
            self.marks.append(Mark(result.blocker.cell, theme.DANGER, "ring", 0.7))
            text = "被挡住了！"
        elif result.hit_wall:
            self.marks.append(Mark(result.hit.cell, (170, 186, 232), "wall", 0.7))
            text = "这堵墙拦着！"
        else:  # pragma: no cover - 理论上不会走到
            text = "飞不出去"
        self.add_toast(text, theme.DANGER, self.cell_center(*result.arrow.cell))

    def add_toast(self, text: str, color: Color, pos: Point) -> None:
        self.toasts.append(Toast(text, color, pos))

    def show_hint(self, arrow) -> None:
        self.hint_cell = arrow.cell
        self.hint_elapsed = 0.0
        self.add_toast("这个箭头可以飞", theme.GOOD, self.cell_center(arrow.x, arrow.y))

    # ------------------------------------------------------------------ 更新

    def update(self, dt: float) -> None:
        self.time += dt
        if self.spawn > 0:
            self.spawn = max(0.0, self.spawn - dt)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt)
        if self.nudge is not None:
            cell, remain = self.nudge
            remain -= dt
            self.nudge = (cell, remain) if remain > 0 else None
        if self.hint_cell is not None:
            self.hint_elapsed += dt
            if self.hint_elapsed >= self.hint_ttl:
                self.hint_cell = None

        for item in list(self.flying):
            item.elapsed += dt
            if item.elapsed >= item.duration:
                self.flying.remove(item)
        for toast in list(self.toasts):
            toast.elapsed += dt
            if toast.elapsed >= toast.ttl:
                self.toasts.remove(toast)
        for mark in list(self.marks):
            mark.elapsed += dt
            if mark.elapsed >= mark.ttl:
                self.marks.remove(mark)

    # ------------------------------------------------------------------ 绘制

    def draw(self, surface: pygame.Surface) -> None:
        if self.board is None:
            return
        dx, dy = self.shake_offset()
        self._draw_panel(surface, dx, dy)
        self._draw_grid(surface, dx, dy)
        self._draw_walls(surface, dx, dy)
        self._draw_hover_tile(surface, dx, dy)
        self._draw_preview(surface, dx, dy)
        self._draw_marks(surface, dx, dy)
        self._draw_arrows(surface, dx, dy)
        self._draw_flying(surface, dx, dy)
        self._draw_hint(surface, dx, dy)
        self._draw_toasts(surface, dx, dy)
        self._draw_flash(surface)

    # -- 各层

    def _draw_panel(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        panel = self.panel.move(dx, dy)
        shapes.panel(surface, panel, radius=26)
        # 面板内部再压一层更暗的底，让箭头更跳
        inner = panel.inflate(-14, -14)
        shapes.rounded_rect(surface, inner, theme.PANEL_INNER, radius=20)
        shapes.rounded_rect(surface, inner, (255, 255, 255, 10), radius=20, width=1)

    def _draw_grid(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        board = self.board
        radius = max(1.0, self.cell * 0.045)
        for gy in range(board.height + 1):
            for gx in range(board.width + 1):
                px = self.origin[0] + gx * self.cell + dx
                py = self.origin[1] + gy * self.cell + dy
                shapes.dot(surface, (px, py), radius, theme.GRID_DOT, 150)

    def _draw_walls(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        inset = max(2.0, self.cell * 0.08)
        radius = max(4, int(self.cell * 0.2))
        for (wx, wy) in self.board.walls:
            center = self.cell_center(wx, wy)
            rect = pygame.Rect(0, 0, self.cell - inset * 2, self.cell - inset * 2)
            rect.center = (int(center[0] + dx), int(center[1] + dy))
            shapes.rounded_rect(surface, rect, (16, 22, 48), radius=radius)
            inner = rect.inflate(-2, -2)
            shapes.rounded_rect(surface, inner, theme.WALL, radius=max(2, radius - 1))
            # 砖缝：一眼就能和箭头区分开
            mortar = (44, 56, 102)
            pygame.draw.line(surface, mortar, (inner.left + 2, inner.centery),
                             (inner.right - 2, inner.centery), 2)
            quarter = inner.width // 4
            pygame.draw.line(surface, mortar, (inner.centerx, inner.top + 2),
                             (inner.centerx, inner.centery), 2)
            pygame.draw.line(surface, mortar, (inner.left + quarter, inner.centery),
                             (inner.left + quarter, inner.bottom - 2), 2)
            pygame.draw.line(surface, mortar, (inner.right - quarter, inner.centery),
                             (inner.right - quarter, inner.bottom - 2), 2)

    def _draw_hover_tile(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        """悬停时把箭头的格子高亮出来，平时不铺底块，棋盘更清爽。"""
        if self.hover is None:
            return
        inset = max(2.0, self.cell * 0.07)
        radius = max(6, int(self.cell * 0.26))
        center = self.cell_center(self.hover.x, self.hover.y)
        rect = pygame.Rect(0, 0, self.cell - inset * 2, self.cell - inset * 2)
        rect.center = (int(center[0] + dx), int(center[1] + dy))
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*theme.TILE_HOVER, 175), layer.get_rect(), border_radius=radius)
        surface.blit(layer, rect.topleft)
        shapes.rounded_rect(surface, rect, theme.TILE_HOVER_EDGE, radius=radius, width=2)

    def _draw_preview(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        """悬停预览：绿色虚线 = 能飞；红色虚线 + 红圈 = 被谁挡住。"""
        arrow = self.hover
        if arrow is None or self.board is None:
            return
        hit = self.board.scan(arrow.x, arrow.y, arrow.direction)
        ray = self.board.ray_cells(arrow.x, arrow.y, arrow.direction, stop_at_blocker=True)
        start = self.cell_center(arrow.x, arrow.y)
        start = (start[0] + dx, start[1] + dy)
        free = hit.kind == "edge"
        color = theme.GOOD if free else theme.DANGER

        empty_cells = [cell for cell in ray if self.board.is_empty(cell[0], cell[1])]
        for index, cell in enumerate(empty_cells):
            center = self.cell_center(cell[0], cell[1])
            radius = self.cell * (0.115 - 0.015 * index / max(1, len(empty_cells)))
            shapes.dot(surface, (center[0] + dx, center[1] + dy), max(1.5, radius), color, 210)

        if free:
            if ray:
                last = self.cell_center(ray[-1][0], ray[-1][1])
            else:
                last = (start[0] - dx, start[1] - dy)
            end = (last[0] + dx + arrow.direction.dx * self.cell * 0.5,
                   last[1] + dy + arrow.direction.dy * self.cell * 0.5)
            shapes.dot(surface, end, max(2.0, self.cell * 0.09), theme.GOOD, 230)
        elif hit.cell is not None:
            blocker_center = self.cell_center(hit.cell[0], hit.cell[1])
            blocker_center = (blocker_center[0] + dx, blocker_center[1] + dy)
            pulse = 0.5 + 0.5 * math.sin(self.time * 7.0)
            shapes.ring(surface, blocker_center, self.cell * (0.46 + 0.05 * pulse), theme.DANGER, 3, 235)

        pulse = 0.5 + 0.5 * math.sin(self.time * 6.0)
        shapes.ring(surface, start, self.cell * (0.44 + 0.035 * pulse), color, 3, 210)

    def _draw_marks(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        for mark in self.marks:
            k = 1.0 - mark.elapsed / mark.ttl
            center = self.cell_center(mark.cell[0], mark.cell[1])
            center = (center[0] + dx, center[1] + dy)
            if mark.kind == "dot":
                shapes.dot(surface, center, max(1.5, self.cell * 0.11 * k), mark.color, int(220 * k))
            elif mark.kind == "ring":
                radius = self.cell * (0.42 + 0.24 * (1 - k))
                shapes.ring(surface, center, radius, mark.color, max(2, int(3 * k) + 1), int(240 * k))
            else:
                radius = self.cell * (0.40 + 0.16 * (1 - k))
                shapes.ring(surface, center, radius, mark.color, 3, int(220 * k))

    def _draw_arrows(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        base_size = self.cell * 0.80
        spawn_k = self.spawn / self.spawn_total if self.spawn_total else 0.0
        for arrow in self.board.arrows.values():
            center = self.cell_center(arrow.x, arrow.y)
            cx, cy = center[0] + dx, center[1] + dy
            scale = 1.0
            if spawn_k > 0:
                # 入场时弹一下：先略大再回正
                scale *= 1.0 + 0.24 * spawn_k * math.sin(spawn_k * math.pi)
            if self.hover is not None and self.hover.id == arrow.id:
                scale *= 1.12
            if self.nudge is not None and self.nudge[0] == arrow.cell:
                _, remain = self.nudge
                k = remain / 0.34
                offset = math.sin(remain * 42) * self.cell * 0.14 * k
                cx += arrow.direction.dx * offset
                cy += arrow.direction.dy * offset
            shapes.draw_arrow(surface, (cx, cy), base_size, arrow.direction.name,
                              theme.arrow_color(arrow.color), scale)

    def _draw_flying(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        base_size = self.cell * 0.80
        for item in self.flying:
            p = item.progress
            ease = p ** 1.6                      # 越飞越快，像被射出去
            color = theme.arrow_color(item.color)
            for back, alpha in ((0.05, 120), (0.10, 76), (0.16, 40)):
                tp = max(0.0, ease - back)
                fade = int(alpha * (1.0 - p) + 12)
                if fade <= 0:
                    continue
                x, y = item.position(tp)
                shapes.draw_arrow(surface, (x + dx, y + dy), base_size, item.direction.name,
                                  color, 1.0, fade)
            x, y = item.position(ease)
            shapes.draw_arrow(surface, (x + dx, y + dy), base_size, item.direction.name, color)

    def _draw_hint(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        if self.hint_cell is None:
            return
        k = 1.0 - self.hint_elapsed / self.hint_ttl
        center = self.cell_center(self.hint_cell[0], self.hint_cell[1])
        center = (center[0] + dx, center[1] + dy)
        pulse = 0.5 + 0.5 * math.sin(self.time * 9.0)
        shapes.ring(surface, center, self.cell * (0.46 + 0.06 * pulse), theme.ACCENT, 3, int(230 * k))
        shapes.ring(surface, center, self.cell * (0.62 + 0.05 * pulse), theme.ACCENT, 2, int(110 * k))

    def _draw_toasts(self, surface: pygame.Surface, dx: float, dy: float) -> None:
        for toast in self.toasts:
            k = toast.elapsed / toast.ttl
            alpha = int(255 * (1.0 - k ** 2))
            y = toast.pos[1] + dy - 32 * k
            x = toast.pos[0] + dx
            # 垫一层小胶囊，免得文字压在箭头上看不清
            width = shapes.text_width(toast.text, 19, True) + 22
            pill = pygame.Rect(0, 0, width, 30)
            pill.center = (int(x), int(y))
            layer = pygame.Surface(pill.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (8, 12, 28, 215), layer.get_rect(), border_radius=15)
            pygame.draw.rect(layer, (*toast.color, 190), layer.get_rect(), width=1, border_radius=15)
            layer.set_alpha(max(0, min(255, alpha)))
            surface.blit(layer, pill.topleft)
            shapes.text(surface, toast.text, pill.center, 19, True, toast.color, shadow=False, alpha=alpha)

    def _draw_flash(self, surface: pygame.Surface) -> None:
        if self.flash <= 0:
            return
        k = self.flash / 0.4
        width = max(3, int(9 * k))
        layer = pygame.Surface((theme.LOGICAL_W, theme.LOGICAL_H), pygame.SRCALPHA)
        pygame.draw.rect(layer, (*theme.DANGER, int(110 * k)), layer.get_rect(), width, border_radius=10)
        surface.blit(layer, (0, 0))
