"""开发辅助：不开窗口把各个界面渲染成 PNG，用来检查排版和配色。

用法（在作业根目录下）::

    python arrow_arrows/tools/screenshot.py

图片会输出到 ``arrow_arrows/tools/shots/``。
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame  # noqa: E402

from arrow_arrows.ui.app import App  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")


def shoot(app: App, name: str, mouse=None, settle: float = 0.016) -> str:
    if mouse is not None:
        pygame.mouse.get_pos = lambda: (int(mouse[0]), int(mouse[1]))  # type: ignore[assignment]
    else:
        pygame.mouse.get_pos = lambda: (-50, -50)  # type: ignore[assignment]
    app.update(settle)
    app.draw()
    # 切场景的第一帧会走淡入动画，截图时把它关掉再画一遍
    app.fade = 0.0
    app.update(0.0)
    app.draw()
    path = os.path.join(OUT_DIR, name)
    pygame.image.save(app.logical, path)
    print("saved", path)
    return path


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    app = App(seed=20240501, persist=False)

    # 主菜单 / 选关 / 说明
    app.state = "menu"
    shoot(app, "01_menu.png")

    app.progress.unlocked = 12
    app.progress.stars = {1: 3, 2: 3, 3: 2, 4: 3, 5: 1, 6: 2, 7: 3, 8: 2, 9: 3, 10: 3, 11: 1}
    app.state = "levels"
    shoot(app, "02_levels.png")

    app.state = "help"
    shoot(app, "03_help.png")

    # 第 10 关：普通视图 / 悬停可飞箭头 / 悬停被挡箭头
    app.start_level(10)
    shoot(app, "04_game_level10.png")

    free_arrow = app.board.free_arrows()[0]
    free_center = app.view.cell_center(free_arrow.x, free_arrow.y)
    shoot(app, "05_hover_free.png", mouse=free_center)

    blocked = app.board.blocked_arrows()
    target = None
    for arrow in blocked:
        hit = app.board.scan(arrow.x, arrow.y, arrow.direction)
        if hit.kind == "arrow" and hit.distance >= 2:
            target = arrow
            break
    target = target or blocked[0]
    blocked_center = app.view.cell_center(target.x, target.y)
    shoot(app, "06_hover_blocked.png", mouse=blocked_center)

    # 点一个被挡住的箭头 → 抖动 + 红框 + 扣血
    app.click_board(blocked_center)
    shoot(app, "07_blocked_flash.png", mouse=blocked_center)

    # 飞出去的瞬间
    app.restart_level()
    free_arrow = app.board.free_arrows()[0]
    app.click_board(app.view.cell_center(free_arrow.x, free_arrow.y))
    shoot(app, "08_flying.png", settle=0.1)

    # 过关弹层
    app.restart_level()
    app.board.arrows.clear()
    app.elapsed = 83.4
    app.mistakes = 0
    app.hints_used = 0
    app.finish_win()
    for _ in range(12):
        app.update(0.05)
        app.draw()
    pygame.image.save(app.logical, os.path.join(OUT_DIR, "09_win.png"))
    print("saved", os.path.join(OUT_DIR, "09_win.png"))

    # 失败弹层 / 暂停
    app.start_level(12)
    app.lives = 0
    app.overlay = "lose"
    app.overlay_t = 0.4
    shoot(app, "10_lose.png")

    app.overlay = "paused"
    shoot(app, "11_pause.png")

    # 大关卡（30 关）看棋盘观感
    app.start_level(30)
    shoot(app, "12_game_level30.png")

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
