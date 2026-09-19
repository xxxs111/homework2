"""核心逻辑层单元测试（不需要 pygame，可直接 ``python -m unittest`` 运行）。"""

from __future__ import annotations

import random
import time
import unittest

from arrow_arrows.core.generator import TOTAL_LEVELS, difficulty_for, generate_level
from arrow_arrows.core.model import (
    Board,
    Direction,
    parse_level,
)
from arrow_arrows.core.solver import find_hint, greedy_solve, is_solvable, unlock_gain

# 抽样关卡：覆盖前期小棋盘、中期迷宫和后期大棋盘
SAMPLE_LEVELS = (1, 2, 4, 6, 8, 10, 14, 18, 22, 26, 30)


class RuleTests(unittest.TestCase):
    """规则层：方向判定、路径检测、点击判定。"""

    def test_right_free_and_blocked(self) -> None:
        board = parse_level(["..>.", "...."])
        arrow = board.arrow_at(2, 0)
        self.assertIsNotNone(arrow)
        result = board.click(arrow)
        self.assertTrue(result.flew)
        self.assertEqual(result.hit.kind, "edge")
        self.assertEqual(result.open_cells, [(3, 0)])
        self.assertEqual(board.exit_steps(arrow), 2)

        blocked_board = parse_level(["..>v", "...."])
        blocked = blocked_board.click(blocked_board.arrow_at(2, 0))
        self.assertFalse(blocked.flew)
        self.assertEqual(blocked.hit.kind, "arrow")
        self.assertEqual(blocked.hit.cell, (3, 0))
        self.assertEqual(blocked.open_cells, [])
        self.assertIs(blocked.blocker, blocked_board.arrow_at(3, 0))

    def test_four_directions(self) -> None:
        board = parse_level([
            "..^..",
            ".....",
            "<..>#",
            ".....",
            "..v..",
        ])
        self.assertTrue(board.is_free(board.arrow_at(2, 0)))          # 上
        self.assertTrue(board.is_free(board.arrow_at(0, 2)))          # 左
        self.assertTrue(board.is_free(board.arrow_at(2, 4)))          # 下
        self.assertFalse(board.is_free(board.arrow_at(3, 2)))         # 右，被墙挡

        up = board.scan(2, 0, Direction.UP)
        self.assertEqual(up.kind, "edge")
        self.assertEqual(up.distance, 1)

        left = board.scan(0, 2, Direction.LEFT)
        self.assertEqual(left.kind, "edge")
        self.assertEqual(left.distance, 1)

        right = board.scan(3, 2, Direction.RIGHT)
        self.assertEqual(right.kind, "wall")
        self.assertEqual(right.cell, (4, 2))
        self.assertEqual(right.distance, 1)

    def test_nearest_blocker_wins(self) -> None:
        board = parse_level(["..>vv", "....."])
        arrow = board.arrow_at(2, 0)
        hit = board.scan(arrow.x, arrow.y, arrow.direction)
        self.assertEqual(hit.cell, (3, 0))
        self.assertEqual(hit.distance, 1)
        self.assertEqual([a.cell for a in board.blockers(arrow)], [(3, 0), (4, 0)])
        self.assertEqual(len(board.arrows), 3)

    def test_blocked_by_wall_has_no_blocker_arrow(self) -> None:
        board = parse_level(["..>#.", "....."])
        result = board.click(board.arrow_at(2, 0))
        self.assertFalse(result.flew)
        self.assertTrue(result.hit_wall)
        self.assertIsNone(result.blocker)
        self.assertEqual(result.hit.cell, (3, 0))

    def test_ray_cells_and_exit_steps(self) -> None:
        board = parse_level([">...#"])
        arrow = board.arrow_at(0, 0)
        self.assertEqual(board.ray_cells(0, 0, Direction.RIGHT), [(1, 0), (2, 0), (3, 0), (4, 0)])
        self.assertEqual(board.ray_cells(0, 0, Direction.RIGHT, stop_at_blocker=True),
                         [(1, 0), (2, 0), (3, 0), (4, 0)])
        self.assertEqual(board.exit_steps(arrow), 5)

    def test_arrow_pointing_away_is_free(self) -> None:
        board = parse_level([
            ".<..",
            "..^.",
        ])
        # (2,1) 朝上，虽然左边 (1,0) 有箭头，但不在它的射线上
        self.assertTrue(board.is_free(board.arrow_at(2, 1)))
        self.assertTrue(board.is_free(board.arrow_at(1, 0)))

    def test_diagonal_never_blocks(self) -> None:
        board = parse_level([
            ".>..",
            "....",
            "v...",
        ])
        blocked = board.blocked_arrows()
        self.assertEqual(blocked, [])

    def test_free_arrow_removal_never_blocks_others(self) -> None:
        """单调性：点掉一个能飞的箭头，不会让别的箭头变得不能飞。"""
        for level in (1, 3, 6, 10, 16):
            board = generate_level(level, random.Random(level * 31 + 7))
            order = greedy_solve(board)
            self.assertIsNotNone(order)
            work = board.clone()
            while work.arrow_count:
                free_before = {a.id for a in work.free_arrows()}
                self.assertTrue(free_before)
                victim = work.arrows[sorted(free_before)[0]]
                work.remove_arrow(victim.id)
                free_after = {a.id for a in work.free_arrows()}
                self.assertTrue(free_before - {victim.id} <= free_after)

    def test_clone_is_independent(self) -> None:
        board = parse_level(["v>..", "...."])
        shadow = board.clone()
        shadow.remove_arrow(board.arrow_at(1, 0))
        self.assertEqual(board.arrow_count, 2)
        self.assertEqual(shadow.arrow_count, 1)
        self.assertIsNotNone(board.arrow_at(1, 0))
        self.assertIsNone(shadow.arrow_at(1, 0))

    def test_blocking_map(self) -> None:
        board = parse_level([
            "..>v",
            "....",
        ])
        mapping = board.blocking_map()
        right_arrow = board.arrow_at(2, 0)
        down_arrow = board.arrow_at(3, 0)
        self.assertEqual(mapping, {right_arrow.id: down_arrow.id})
        self.assertTrue(board.is_free(down_arrow))

    def test_mask_consistency_after_removal(self) -> None:
        board = parse_level([
            "v>..",
            "....",
        ])
        first = board.arrow_at(0, 0)
        board.remove_arrow(first.id)
        self.assertTrue(board.is_empty(0, 0))
        self.assertEqual(board.arrow_count, 1)
        # 掩码没清干净的话，(0,0) 会被当成占用，下面的断言就会失败
        self.assertIsNone(board.arrow_at(0, 0))
        self.assertTrue(board.is_free(board.arrow_at(1, 0)))

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            parse_level(["..", "..."])
        with self.assertRaises(ValueError):
            parse_level(["..x"])
        board = Board(3, 3)
        board.add_wall(1, 1)
        with self.assertRaises(ValueError):
            board.add_arrow(1, 1, Direction.UP)


class SolverTests(unittest.TestCase):
    def test_greedy_solve_handmade(self) -> None:
        board = parse_level([
            "..>v",
            "..v.",
            "....",
        ])
        order = greedy_solve(board)
        self.assertIsNotNone(order)
        self.assertEqual(len(order), 3)
        first = board.arrows[order[0]]
        self.assertTrue(board.is_free(first))

    def test_find_hint_returns_free_arrow(self) -> None:
        board = parse_level([
            "..>v",
            "..v.",
            "....",
        ])
        hint = find_hint(board)
        self.assertIsNotNone(hint)
        self.assertTrue(board.is_free(hint))
        self.assertGreaterEqual(unlock_gain(board, hint), 0)

    def test_unsolvable_board_is_detected(self) -> None:
        # 箭头被墙永久堵死：这是生成器必须避免的非法关卡
        board = parse_level([">#.."])
        self.assertFalse(is_solvable(board))
        self.assertIsNone(greedy_solve(board))


class GeneratorTests(unittest.TestCase):
    LEVELS = SAMPLE_LEVELS

    def test_every_generated_level_is_solvable(self) -> None:
        for level in self.LEVELS:
            for seed in (1, 7, 2024):
                board = generate_level(level, random.Random(seed))
                with self.subTest(level=level, seed=seed):
                    self.assertTrue(is_solvable(board))
                    self.assertGreaterEqual(board.arrow_count, 4)
                    self.assertGreaterEqual(len(board.free_arrows()), 1)

    def test_generated_board_is_consistent(self) -> None:
        for level in self.LEVELS:
            board = generate_level(level, random.Random(level * 13 + 5))
            with self.subTest(level=level):
                occupied = list(board.arrows.values())
                cells = [a.cell for a in occupied]
                self.assertEqual(len(cells), len(set(cells)))            # 不重叠
                for arrow in occupied:
                    self.assertTrue(board.in_bounds(arrow.x, arrow.y))
                    self.assertNotIn(arrow.cell, board.walls)            # 不和墙重合
                # 每个箭头都必须最终能飞出去（贪心解算过程会覆盖这一点）
                self.assertIsNotNone(greedy_solve(board))

    def test_difficulty_is_monotonic(self) -> None:
        previous = difficulty_for(1)
        for level in range(2, TOTAL_LEVELS + 1):
            current = difficulty_for(level)
            self.assertGreaterEqual(current.size, previous.size)
            self.assertGreaterEqual(current.arrows, previous.arrows)
            self.assertLessEqual(current.max_free, previous.max_free)
            previous = current

    def test_generation_is_deterministic_per_seed(self) -> None:
        first = generate_level(9, random.Random(123))
        second = generate_level(9, random.Random(123))
        self.assertEqual(first.to_text(), second.to_text())

    def test_different_seeds_give_different_layouts(self) -> None:
        first = generate_level(12, random.Random(1))
        second = generate_level(12, random.Random(2))
        self.assertNotEqual(first.to_text(), second.to_text())


class GenerationQualityReport(unittest.TestCase):
    """不是断言，而是打印生成质量与耗时，方便调参和写实验报告。"""

    def test_report(self) -> None:
        print("\n关卡  边长  箭头  开局自由  平均生成耗时(ms)")
        for level in SAMPLE_LEVELS:
            times = []
            arrows = []
            frees = []
            for seed in range(5):
                start = time.perf_counter()
                board = generate_level(level, random.Random(seed))
                times.append((time.perf_counter() - start) * 1000)
                arrows.append(board.arrow_count)
                frees.append(len(board.free_arrows()))
            diff = difficulty_for(level)
            print(f"{level:>4}  {diff.size:>4}  {sum(arrows)/len(arrows):>4.1f}  "
                  f"{sum(frees)/len(frees):>8.1f}  {sum(times)/len(times):>16.1f}")
        print()


if __name__ == "__main__":
    unittest.main(verbosity=2)
