"""逐关自动试玩，打印「每关都能通关」的验证报告。

作业要求「每个关卡都应由本人实际试玩，确保存在合理的通关顺序」。这个脚本用
和玩家完全相同的点击链路（``App.click_board``）把 30 关全自动打通一遍，
输出每关的箭头数、点击步数、失误次数和通关结果，可以作为试玩记录贴进博客。

    python arrow_arrows/tools/verify_levels.py            # 全部 30 关
    python arrow_arrows/tools/verify_levels.py 5          # 每关跑 5 种随机布局
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame  # noqa: E402

from arrow_arrows.core import TOTAL_LEVELS, difficulty_for, find_hint  # noqa: E402
from arrow_arrows.ui.app import App  # noqa: E402


def play_once(app: App, level: int) -> dict:
    """按「先点能飞的箭头」策略把一关打完，返回统计信息。"""
    app.start_level(level)
    arrows = app.board.arrow_count
    body_cells = len(app.board.occupied_cells())
    size = app.board.width
    steps = 0
    started = time.perf_counter()
    guard = arrows * 4 + 40
    while app.board.arrow_count and guard > 0:
        guard -= 1
        arrow = find_hint(app.board)
        if arrow is None:                     # 理论上不会发生
            break
        app.click_board(app.view.cell_center(*arrow.head))
        app.update(0.01)
        steps += 1
    for _ in range(40):                       # 让飞出动画和过关弹层走完
        app.update(0.05)
    seconds = time.perf_counter() - started
    return {
        "level": level,
        "size": size,
        "arrows": arrows,
        "cells": body_cells,
        "steps": steps,
        "mistakes": app.mistakes,
        "stars": app.stars,
        "overlay": app.overlay or "none",
        "seconds": seconds,
    }


def main() -> int:
    rounds = 1
    if len(sys.argv) > 1:
        rounds = max(1, int(sys.argv[1]))

    app = App(seed=20240501, persist=False)
    print(f"== 逐关自动试玩（每关 {rounds} 种随机布局）==")
    print("关卡  边长  箭头数  占格  点击步数  失误  星级  结果   耗时(s)")

    failures = 0
    for level in range(1, TOTAL_LEVELS + 1):
        for _ in range(rounds):
            info = play_once(app, level)
            passed = info["overlay"] == "win" and info["mistakes"] == 0 and info["steps"] == info["arrows"]
            failures += 0 if passed else 1
            print(f"{info['level']:>4}  {info['size']:>4}  {info['arrows']:>6}  {info['cells']:>4}  "
                  f"{info['steps']:>8}  {info['mistakes']:>4}  {info['stars']:>4}  "
                  f"{'通关' if passed else '异常':<4}  {info['seconds']:>6.2f}")

    print()
    print("难度曲线（生成参数）：")
    print("关卡  边长  墙  目标箭头  走廊上限  自由上限")
    for level in (1, 5, 10, 15, 20, 25, 30):
        d = difficulty_for(level)
        print(f"{d.level:>4}  {d.size:>4}  {d.walls:>2}  {d.arrows:>8}  {d.chain_len:>8}  {d.max_free:>8}")

    pygame.quit()
    print()
    if failures:
        print(f"有 {failures} 次试玩没能正常通关，需要检查生成器！")
        return 1
    print(f"全部 {TOTAL_LEVELS * rounds} 次试玩均正常通关（零失误）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
