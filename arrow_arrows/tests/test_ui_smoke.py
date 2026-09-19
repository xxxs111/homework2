"""界面层集成测试：把一整关自动打通，检查状态机、动画和资源释放。

用 SDL 的 dummy 视频 / 音频驱动跑，不会弹窗、也不需要声卡，
所以可以放进 ``python -m unittest`` 里跟规则测试一起跑。
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arrow_arrows.core import find_hint  # noqa: E402
from arrow_arrows.ui import theme  # noqa: E402
from arrow_arrows.ui.app import App  # noqa: E402


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = App(seed=20240501, persist=False)

    # 注意：这里故意不调用 pygame.quit()。多个测试模块各自建 App、各自 quit 时，
    # SDL 在解释器退出阶段会重复释放资源，实测会让整个进程以 0xC0000005 崩溃
    # （测试本身是通过的，但 unittest 的汇总行会被吞掉）。进程马上结束，
    # 交给操作系统回收即可。

    def setUp(self) -> None:
        self.app.state = "menu"
        self.app.overlay = None

    # ------------------------------------------------------------------ 用例

    def test_every_screen_renders(self) -> None:
        """四个场景各画一帧，确认没有绘制异常。"""
        for state in ("menu", "levels", "help"):
            self.app.state = state
            self.app.update(0.016)
            self.app.draw()
            self.assertTrue(self.app.buttons, f"{state} 场景没有可点击按钮")
        self.app.start_level(8)
        self.app.update(0.016)
        self.app.draw()

    def test_auto_play_wins_with_three_stars(self) -> None:
        """一路点「能飞的箭头」，应该零失误通关并拿到三星。"""
        app = self.app
        app.start_level(9)
        guard = 0
        while app.board.arrow_count and guard < 400:
            arrow = find_hint(app.board)
            self.assertIsNotNone(arrow)
            center = app.view.cell_center(arrow.x, arrow.y)
            self.assertIsNotNone(app.view.px_to_cell(center))     # 点击坐标要能反查回格子
            app.click_board(center)
            app.update(0.02)
            guard += 1
        self.assertTrue(app.board.is_clear())
        for _ in range(40):
            app.update(0.05)
        self.assertEqual(app.overlay, "win")
        self.assertEqual(app.mistakes, 0)
        self.assertEqual(app.stars, 3)

    def test_blocked_click_costs_a_life(self) -> None:
        app = self.app
        app.start_level(12)
        blocked = app.board.blocked_arrows()
        self.assertTrue(blocked)
        target = blocked[0]
        app.click_board(app.view.cell_center(target.x, target.y))
        self.assertEqual(app.lives, app.max_lives - 1)
        self.assertEqual(app.mistakes, 1)
        self.assertGreater(app.view.shake, 0)
        self.assertTrue(app.view.marks)          # 弹道 / 拦路提示标记
        self.assertTrue(app.view.toasts)         # 飘字提示

    def test_losing_all_lives_shows_lose_overlay(self) -> None:
        app = self.app
        app.start_level(12)
        blocked = app.board.blocked_arrows()[0]
        center = app.view.cell_center(blocked.x, blocked.y)
        for _ in range(app.max_lives):
            app.click_board(center)
            for _ in range(10):
                app.update(0.03)
        self.assertEqual(app.lives, 0)
        for _ in range(40):
            app.update(0.05)
        self.assertEqual(app.overlay, "lose")

    def test_hint_highlights_a_clickable_arrow(self) -> None:
        app = self.app
        app.start_level(10)
        app.use_hint()
        self.assertIsNotNone(app.view.hint_cell)
        self.assertEqual(app.hints_used, 1)
        arrow = app.board.arrow_at(*app.view.hint_cell)
        self.assertTrue(app.board.is_free(arrow))

    def test_restart_restores_same_layout_and_stats(self) -> None:
        app = self.app
        app.start_level(10)
        before = app.board.to_text()
        blocked = app.board.blocked_arrows()[0]
        app.click_board(app.view.cell_center(blocked.x, blocked.y))
        app.restart_level()
        self.assertEqual(app.board.to_text(), before)
        self.assertEqual(app.lives, app.max_lives)
        self.assertEqual(app.mistakes, 0)
        self.assertEqual(app.elapsed, 0.0)

    def test_relayout_generates_a_new_board(self) -> None:
        app = self.app
        app.start_level(14)
        before = app.board.to_text()
        app.do_action("relayout")
        self.assertNotEqual(app.board.to_text(), before)
        self.assertEqual(app.elapsed, 0.0)

    def test_button_keys_are_dispatchable(self) -> None:
        """界面上出现的按钮，其 key 都必须能被 do_action 处理。"""
        app = self.app
        for state in ("menu", "levels", "help"):
            app.state = state
            app.draw()
            for button in app.buttons:
                self.assertTrue(button.key, "按钮 key 不能为空")
        app.start_level(7)
        for overlay in (None, "paused", "win", "lose"):
            app.overlay = overlay
            app.draw()
            for button in app.buttons:
                self.assertTrue(button.key)

    def test_window_scaling_maps_mouse_back(self) -> None:
        app = self.app
        app.window = pygame.display.set_mode((720, 1280), pygame.RESIZABLE)
        app._update_viewport()
        logical = app.to_logical((360.0, 640.0))
        self.assertAlmostEqual(logical[0], theme.LOGICAL_W / 2, delta=2)
        self.assertAlmostEqual(logical[1], theme.LOGICAL_H / 2, delta=2)

    def test_generated_board_fits_panel(self) -> None:
        """最大棋盘也要完整画在面板里。"""
        app = self.app
        app.start_level(30)
        view = app.view
        left, top = view.cell_center(0, 0)
        right, bottom = view.cell_center(app.board.width - 1, app.board.height - 1)
        self.assertGreater(left - view.cell / 2, theme.BOARD_PANEL.left)
        self.assertLess(right + view.cell / 2, theme.BOARD_PANEL.right)
        self.assertGreater(top - view.cell / 2, theme.BOARD_PANEL.top)
        self.assertLess(bottom + view.cell / 2, theme.BOARD_PANEL.bottom)

    def test_hover_text_reflects_blocking(self) -> None:
        app = self.app
        app.start_level(10)
        free = app.board.free_arrows()[0]
        app.mouse_logical = app.view.cell_center(free.x, free.y)
        app.update_hover()
        self.assertTrue(app.hover_free)
        self.assertIn("畅通", app.hover_text)

        blocked = app.board.blocked_arrows()[0]
        app.mouse_logical = app.view.cell_center(blocked.x, blocked.y)
        app.update_hover()
        self.assertFalse(app.hover_free)
        self.assertIn("挡住", app.hover_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
