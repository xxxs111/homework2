"""游戏主程序：窗口、主循环、状态机、输入与「一次点击」的全部处理。

状态机很简单：``menu / levels / help / game``，其中 ``game`` 还可以叠加一个弹层
（``paused / win / lose``）。核心流程：

    点击棋盘 → 交给 core 判定能不能飞
        ├─ 能飞 → 从棋盘移除 + 飞出动画 + 音效 → 清空则过关
        └─ 不能 → 抖动/闪红/圈出拦路箭头 + 扣一颗心 → 心用完则失败
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

import pygame

from ..core import TOTAL_LEVELS, find_hint, generate_level
from ..core.model import Board
from . import scenes, shapes, theme
from .audio import Audio
from .board_view import BoardView
from .storage import Progress
from .widgets import Button

MAX_LIVES = 3


class App:
    """游戏主体。"""

    def __init__(self, seed: Optional[int] = None, persist: bool = True) -> None:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("一箭又一箭 · Python + Pygame")
        self.window = pygame.display.set_mode((theme.LOGICAL_W, theme.LOGICAL_H), pygame.RESIZABLE)
        self.logical = pygame.Surface((theme.LOGICAL_W, theme.LOGICAL_H)).convert()
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.progress = Progress.load()
        # 自动化测试 / 截图 / 试玩脚本用 persist=False，免得把玩家的存档解锁进度和最好成绩改掉
        self.persist = persist
        self.rng = random.Random(seed)
        self.total_levels = TOTAL_LEVELS

        # 背景：一张预渲染好的图（深色渐变 + 上下两处柔光），每帧只 blit 一次
        self.backdrop = shapes.vertical_gradient((theme.LOGICAL_W, theme.LOGICAL_H),
                                                 theme.BG_TOP, theme.BG_BOTTOM)
        top_glow = shapes.radial_glow(340, theme.GLOW, 34)
        self.backdrop.blit(top_glow, top_glow.get_rect(center=(theme.LOGICAL_W // 2, 120)))
        bottom_glow = shapes.radial_glow(280, theme.GLOW, 18)
        self.backdrop.blit(bottom_glow, bottom_glow.get_rect(center=(theme.LOGICAL_W // 2,
                                                                    theme.LOGICAL_H - 40)))

        self.view = BoardView(theme.BOARD_PANEL)
        self.viewport: Tuple[float, float, float] = (0.0, 0.0, 1.0)
        self.mouse_logical: Tuple[float, float] = (-100.0, -100.0)
        self.buttons: List[Button] = []
        self.pressed: Optional[str] = None

        self.state = "menu"
        self.overlay: Optional[str] = None
        self.overlay_t = 0.0
        self.fade = 1.0
        self._screen_key: Tuple[str, Optional[str]] = ("", None)
        self.running = True

        self.level = min(max(1, self.progress.unlocked), self.total_levels)
        self.board: Optional[Board] = None
        self.initial_board: Optional[Board] = None
        self.lives = MAX_LIVES
        self.max_lives = MAX_LIVES
        self.mistakes = 0
        self.hints_used = 0
        self.stars = 0
        self.elapsed = 0.0
        self.total_arrows = 0
        self.pending_win = 0.0
        self.pending_lose = 0.0
        self.hover_text = ""
        self.hover_free = False

    # ================================================================== 主循环

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(theme.FPS) / 1000.0)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            self.present()
        if self.persist:
            self.progress.save()
        pygame.quit()

    # ================================================================== 事件

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            size = (max(360, event.w), max(520, event.h))
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            self._update_viewport()
        elif event.type == pygame.KEYDOWN:
            self.on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            position = self.to_logical(event.pos)
            self.mouse_logical = position
            self.on_click(position)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed = None

    def on_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.state == "game":
                if self.overlay in ("win", "lose"):
                    self.state = "menu"
                    self.overlay = None
                else:
                    self.overlay = None if self.overlay else "paused"
                    self.overlay_t = 0.0
                    self.audio.play("click")
            elif self.state in ("levels", "help"):
                self.state = "menu"
            else:
                self.running = False
            return

        if key == pygame.K_m:
            self.audio.toggle_mute()
            return

        if self.state == "game":
            if self.overlay == "win":
                if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_n):
                    self.do_action("next" if self.level < self.total_levels else "restart")
                elif key == pygame.K_r:
                    self.do_action("restart")
                return
            if self.overlay == "lose":
                if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r):
                    self.do_action("restart")
                return
            if self.overlay == "paused":
                if key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.do_action("resume")
                elif key == pygame.K_r:
                    self.do_action("restart")
                elif key == pygame.K_n:
                    self.do_action("relayout")
                return
            if key == pygame.K_r:
                self.do_action("restart")
            elif key == pygame.K_n:
                self.do_action("relayout")
            elif key == pygame.K_h:
                self.do_action("hint")

    def on_click(self, position: Tuple[float, float]) -> None:
        for button in self.buttons:
            if button.hit(position):
                self.pressed = button.key
                self.audio.play("click")
                self.do_action(button.key)
                return
        if self.state == "game" and self.overlay is None:
            self.click_board(position)

    def do_action(self, key: str) -> None:
        if key == "quit":
            self.running = False
        elif key == "start":
            self.start_level(min(self.progress.unlocked, self.total_levels))
        elif key == "levels":
            self.state = "levels"
            self.overlay = None
        elif key == "help":
            self.state = "help"
        elif key == "menu":
            self.state = "menu"
            self.overlay = None
        elif key == "pause":
            if self.state == "game" and self.overlay is None:
                self.overlay = "paused"
                self.overlay_t = 0.0
        elif key == "resume":
            self.overlay = None
        elif key == "restart":
            self.restart_level()
        elif key == "relayout":
            self.start_level(self.level)
        elif key == "hint":
            self.use_hint()
        elif key == "next":
            self.start_level(min(self.level + 1, self.total_levels))
        elif key.startswith("level:"):
            self.start_level(int(key.split(":", 1)[1]))

    # ================================================================== 关卡流程

    def start_level(self, level: int) -> None:
        """生成并开始第 ``level`` 关（重新随机布局）。"""
        self.level = max(1, min(int(level), self.total_levels))
        self._draw_loading()
        board = generate_level(self.level, self.rng)
        self.initial_board = board.clone()
        self._begin(board)

    def restart_level(self) -> None:
        """重开本关：布局不变，重新挑战。"""
        if self.initial_board is None:
            self.start_level(self.level)
            return
        self._begin(self.initial_board.clone())

    def _begin(self, board: Board) -> None:
        self.board = board
        self.lives = self.max_lives
        self.mistakes = 0
        self.hints_used = 0
        self.elapsed = 0.0
        self.total_arrows = board.arrow_count
        self.pending_win = 0.0
        self.pending_lose = 0.0
        self.stars = 0
        self.hover_text = ""
        self.overlay = None
        self.overlay_t = 0.0
        self.view.set_board(board, self.level)
        self.state = "game"

    def _draw_loading(self) -> None:
        """生成关卡大约要十几毫秒，但大棋盘偶尔会久一点，给个提示帧。"""
        scenes.draw_background(self.logical, self)
        shapes.text(self.logical, f"正在生成第 {self.level} 关…",
                    (theme.LOGICAL_W / 2, theme.LOGICAL_H / 2), 26, True, theme.TEXT)
        shapes.text(self.logical, "保证可解 · 全部随机生成",
                    (theme.LOGICAL_W / 2, theme.LOGICAL_H / 2 + 34), 16, False, theme.TEXT_MUTED)
        self.present()

    def click_board(self, position: Tuple[float, float]) -> None:
        if self.board is None:
            return
        cell = self.view.px_to_cell(position)
        if cell is None:
            return
        arrow = self.board.arrow_at(cell[0], cell[1])
        if arrow is None:
            self.audio.play("click")
            return

        result = self.board.click(arrow)
        if result.flew:
            self.board.remove_arrow(arrow.id)
            self.view.spawn_flying(arrow)
            self.audio.play("fly")
            if self.board.is_clear():
                self.pending_win = 0.55
        else:
            self.mistakes += 1
            self.lives -= 1
            self.view.spawn_blocked(result)
            self.audio.play("blocked")
            if self.lives <= 0:
                self.pending_lose = 1.0

    def use_hint(self) -> None:
        if self.board is None or self.overlay is not None:
            return
        arrow = find_hint(self.board)
        if arrow is None:
            return
        self.hints_used += 1
        self.view.show_hint(arrow)
        self.audio.play("hint")

    def finish_win(self) -> None:
        self.stars = self._stars_for_result()
        self.overlay = "win"
        self.overlay_t = 0.0
        self.audio.play("win")
        if self.persist:
            self.progress.record(self.level, self.stars, self.elapsed, self.total_levels)

    def _stars_for_result(self) -> int:
        """三星：零失误零提示；两星：失误 + 提示 ≤ 2；其余一星。"""
        penalty = self.mistakes + self.hints_used
        if penalty == 0:
            return 3
        if penalty <= 2:
            return 2
        return 1

    # ================================================================== 更新

    def _update_viewport(self) -> None:
        win_w, win_h = self.window.get_size()
        scale = min(win_w / theme.LOGICAL_W, win_h / theme.LOGICAL_H)
        if scale <= 0:
            scale = 1.0
        self.viewport = ((win_w - theme.LOGICAL_W * scale) / 2,
                         (win_h - theme.LOGICAL_H * scale) / 2,
                         scale)

    def to_logical(self, pos: Tuple[float, float]) -> Tuple[float, float]:
        ox, oy, scale = self.viewport
        return ((pos[0] - ox) / scale, (pos[1] - oy) / scale)

    def update(self, dt: float) -> None:
        self._update_viewport()
        self.mouse_logical = self.to_logical(pygame.mouse.get_pos())
        self.view.update(dt)
        if self.fade > 0:
            self.fade = max(0.0, self.fade - dt * 3.0)

        if self.state != "game" or self.board is None:
            self.view.hover = None
            return

        if self.overlay is not None:
            self.overlay_t += dt
            self.view.hover = None
            self.hover_text = ""
            return

        if self.pending_win > 0:
            self.pending_win -= dt
            if self.pending_win <= 0:
                self.finish_win()
                return
        elif self.pending_lose > 0:
            self.pending_lose -= dt
            if self.pending_lose <= 0:
                self.overlay = "lose"
                self.overlay_t = 0.0
                self.audio.play("lose")
                return
        else:
            self.elapsed += dt

        self.update_hover()

    def update_hover(self) -> None:
        cell = self.view.px_to_cell(self.mouse_logical)
        arrow = self.board.arrow_at(cell[0], cell[1]) if (cell and self.board) else None
        self.view.hover = arrow
        if arrow is None:
            self.hover_text = ""
            self.hover_free = False
            return
        hit = self.board.scan(arrow.x, arrow.y, arrow.direction)
        if hit.kind == "edge":
            self.hover_free = True
            symbol = {"UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→"}[arrow.direction.name]
            self.hover_text = f"{symbol} 前方畅通，可以飞出去"
        else:
            self.hover_free = False
            if hit.kind == "wall":
                self.hover_text = "× 前方有墙，飞不出去"
            else:
                blocker = self.board.arrow_at(hit.cell[0], hit.cell[1]) if hit.cell else None
                direction = blocker.direction.label if blocker else "?"
                self.hover_text = f"× 被 {hit.distance} 格外那个朝{direction}的箭头挡住了"

    # ================================================================== 绘制

    def draw(self) -> None:
        # 切换界面 / 弹层时做一次淡入，观感更顺
        key = (self.state, self.overlay)
        if key != self._screen_key:
            self._screen_key = key
            self.fade = 1.0

        # 每帧重建按钮列表：绘制与命中判定用的是同一份数据
        if self.state == "menu":
            self.buttons = scenes.draw_menu(self.logical, self)
        elif self.state == "levels":
            self.buttons = scenes.draw_level_select(self.logical, self)
        elif self.state == "help":
            self.buttons = scenes.draw_help(self.logical, self)
        else:
            self.buttons = scenes.draw_game(self.logical, self)
            if self.overlay == "paused":
                self.buttons = scenes.draw_pause(self.logical, self)
            elif self.overlay == "win":
                self.buttons = scenes.draw_win(self.logical, self)
            elif self.overlay == "lose":
                self.buttons = scenes.draw_lose(self.logical, self)

        if self.fade > 0:
            layer = pygame.Surface((theme.LOGICAL_W, theme.LOGICAL_H))
            layer.fill(theme.BG_BOTTOM)
            layer.set_alpha(int(220 * min(1.0, self.fade)))
            self.logical.blit(layer, (0, 0))

    def present(self) -> None:
        ox, oy, scale = self.viewport
        size = (max(1, int(theme.LOGICAL_W * scale)), max(1, int(theme.LOGICAL_H * scale)))
        if size == (theme.LOGICAL_W, theme.LOGICAL_H):
            frame = self.logical
        else:
            frame = pygame.transform.smoothscale(self.logical, size)
        self.window.fill((6, 8, 22))
        self.window.blit(frame, (int(ox), int(oy)))
        pygame.display.flip()
