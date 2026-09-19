"""一箭又一箭（Arrow a Row）——Python + Pygame 小游戏。

包结构::

    arrow_arrows/
        __main__.py        入口（python -m arrow_arrows）
        main.py            入口（python arrow_arrows/main.py）
        core/              纯逻辑层：棋盘、规则、关卡生成、求解（可单独测试）
        ui/                界面层：主题、图形、音效、存档、棋盘视图、场景
        tests/             单元测试与冒烟脚本
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
