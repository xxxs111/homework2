"""对照作业测试表 T01–T06 的自动化用例。

作业要求「对程序进行测试并记录过程与结果」，这里把 T01–T06 逐条写成可重复运行的
自动化测试；每条用例都会打印一行「实际结果」，方便直接抄进博客/报告的测试表。

    T01 点击前方无阻挡的箭头        → 箭头飞出棋盘并消失
    T02 点击前方有阻挡的箭头        → 箭头不消失，失误次数减 1
    T03 点击位于边缘且朝向棋盘外的箭头 → 箭头正常消失，不发生越界错误
    T04 消除本关全部箭头            → 显示通关并进入下一关
    T05 失误次数耗尽                → 显示失败并允许重新开始
    T06 游戏进行中重新开始          → 箭头布局和失误次数恢复
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from arrow_arrows.core import find_hint, parse_level  # noqa: E402
from arrow_arrows.ui.app import App  # noqa: E402


def report(code: str, content: str, expected: str, actual: str, passed: bool) -> None:
    print(f"\n[{code}] {content}\n      预期：{expected}\n      实际：{actual}\n      结果：{'通过' if passed else '不通过'}")


class AssignmentCaseTests(unittest.TestCase):
    """T01–T06：作业要求逐条验证。"""

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

    # ------------------------------------------------------------------ T01

    def test_t01_click_free_arrow(self) -> None:
        app = self.app
        app.start_level(5)
        arrow = app.board.free_arrows()[0]
        before = app.board.arrow_count
        head = arrow.head
        app.click_board(app.view.cell_center(*head))
        self.assertEqual(app.board.arrow_count, before - 1)
        self.assertIsNone(app.board.arrow_at(*head))
        self.assertTrue(app.view.flying, "应该开始播放飞出动画")
        report("T01", "点击前方无阻挡的箭头", "箭头飞出棋盘并消失",
               f"箭头数 {before} → {app.board.arrow_count}，该格已空，飞出动画 {len(app.view.flying)} 个", True)

    # ------------------------------------------------------------------ T02

    def test_t02_click_blocked_arrow(self) -> None:
        app = self.app
        app.start_level(6)
        before = app.board.arrow_count
        blocked = app.board.blocked_arrows()[0]
        head = blocked.head
        app.click_board(app.view.cell_center(*head))
        self.assertEqual(app.board.arrow_count, before, "被挡住的箭头不应该消失")
        self.assertEqual(app.lives, app.max_lives - 1, "失误次数应减 1")
        self.assertEqual(app.mistakes, 1)
        self.assertIsNotNone(app.board.arrow_at(*head))
        self.assertGreater(app.view.shake, 0, "应该有碰撞抖动反馈")
        report("T02", "点击前方有阻挡的箭头", "箭头不消失，失误次数减 1",
               f"箭头数仍为 {app.board.arrow_count}，剩余机会 {app.lives}/{app.max_lives}，"
               f"抖动={app.view.shake:.2f}s，飘字={len(app.view.toasts)}条", True)

    # ------------------------------------------------------------------ T03

    def test_t03_edge_arrow_pointing_outside(self) -> None:
        """边缘且朝外的箭头不能越界：它前方没有格子，必须直接判定为可飞。"""
        board = parse_level([
            "<..^",
            "....",
            "....",
            "v..>",
        ])
        app = self.app
        app._begin(board)
        heads = [(0, 0), (3, 0), (3, 3), (0, 3)]      # 左 / 上 / 右 / 下 四个贴边朝外的箭头
        for head in heads:
            arrow = app.board.arrow_at(*head)
            self.assertIsNotNone(arrow)
            self.assertTrue(app.board.is_free(arrow), f"{head} 朝外应当可以飞")
            self.assertEqual(app.board.exit_steps(arrow), 1)
        for head in heads:
            app.click_board(app.view.cell_center(*head))     # 不允许抛 IndexError / 越界
        self.assertTrue(app.board.is_clear())
        for _ in range(40):
            app.update(0.05)
        self.assertEqual(app.overlay, "win")
        report("T03", "点击位于边缘且朝向棋盘外的箭头", "箭头正常消失，不发生越界错误",
               f"4 个边缘朝外箭头全部飞出，棋盘已清空，弹层={app.overlay}", True)

    # ------------------------------------------------------------------ T04

    def test_t04_clear_level_and_go_next(self) -> None:
        app = self.app
        app.start_level(4)
        level_before = app.level
        guard = 0
        while app.board.arrow_count and guard < 300:
            arrow = find_hint(app.board)
            app.click_board(app.view.cell_center(*arrow.head))
            app.update(0.02)
            guard += 1
        for _ in range(40):
            app.update(0.05)
        self.assertEqual(app.overlay, "win")
        self.assertEqual(app.mistakes, 0)
        stars = app.stars
        app.do_action("next")
        report("T04", "消除本关全部箭头", "显示通关并进入下一关",
               f"本关用 {guard} 步清空、失误 0、星级 {stars}；点「下一关」后进入第 {app.level} 关"
               f"（原第 {level_before} 关），当前弹层={app.overlay}", app.overlay is None)

    # ------------------------------------------------------------------ T05

    def test_t05_lives_run_out_then_restart(self) -> None:
        app = self.app
        app.start_level(8)
        blocked = app.board.blocked_arrows()[0]
        center = app.view.cell_center(*blocked.head)
        for _ in range(app.max_lives):
            app.click_board(center)
            for _ in range(10):
                app.update(0.03)
        self.assertEqual(app.lives, 0)
        for _ in range(40):
            app.update(0.05)
        self.assertEqual(app.overlay, "lose")
        overlay_after_lose = app.overlay
        app.do_action("restart")
        self.assertEqual(app.lives, app.max_lives)
        self.assertEqual(app.overlay, None)
        report("T05", "失误次数耗尽", "显示失败并允许重新开始",
               f"失误 {app.max_lives} 次后弹层={overlay_after_lose}；点「再来一次」后"
               f"剩余机会恢复到 {app.lives}/{app.max_lives}、弹层已关闭={app.overlay is None}", True)

    # ------------------------------------------------------------------ T06

    def test_t06_restart_in_the_middle(self) -> None:
        app = self.app
        app.start_level(9)
        layout_before = app.board.to_text()
        free = app.board.free_arrows()[0]
        blocked = app.board.blocked_arrows()[0]
        app.click_board(app.view.cell_center(*free.head))
        app.click_board(app.view.cell_center(*blocked.head))
        self.assertEqual(app.mistakes, 1)
        changed = app.board.to_text()
        app.do_action("restart")
        self.assertEqual(app.board.to_text(), layout_before)
        self.assertNotEqual(changed, layout_before, "重开前棋盘应该确实被改动过")
        self.assertEqual(app.lives, app.max_lives)
        self.assertEqual(app.mistakes, 0)
        self.assertEqual(app.elapsed, 0.0)
        report("T06", "游戏进行中重新开始", "箭头布局和失误次数恢复",
               f"飞 1 个 + 撞 1 次后，布局回到初始状态={app.board.to_text() == layout_before}，"
               f"剩余机会 {app.lives}/{app.max_lives}，失误归零={app.mistakes == 0}", True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
