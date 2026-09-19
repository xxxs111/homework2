"""命令行入口：``python arrow_arrows/main.py``（也可以 ``python -m arrow_arrows``）。

可选参数：

    --level N   直接跳到第 N 关（调试 / 演示用）
    --seed N    固定随机种子，用于复现某一局的棋盘布局
"""

from __future__ import annotations

import os
import sys


def _ensure_package_importable() -> None:
    """支持「直接 python arrow_arrows/main.py」这种跑法。"""
    if __package__ in (None, ""):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)


_ensure_package_importable()

from arrow_arrows.core import TOTAL_LEVELS      # noqa: E402
from arrow_arrows.ui.app import App             # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    seed = None
    level = None
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--seed" and index + 1 < len(args):
            seed = int(args[index + 1])
            index += 2
            continue
        if token == "--level" and index + 1 < len(args):
            level = int(args[index + 1])
            index += 2
            continue
        if token in ("-h", "--help"):
            print(__doc__)
            return 0
        index += 1

    app = App(seed=seed)
    if level is not None:
        app.start_level(max(1, min(level, TOTAL_LEVELS)))
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
