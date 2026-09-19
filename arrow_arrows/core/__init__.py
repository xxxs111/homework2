"""核心逻辑层：不依赖 pygame，可脱离界面单独运行与测试。"""

from .model import (
    ALL_DIRECTIONS,
    Arrow,
    Board,
    Cell,
    ClickResult,
    Direction,
    Hit,
    parse_level,
)
from .generator import TOTAL_LEVELS, Difficulty, difficulty_for, generate_level
from .solver import find_hint, greedy_solve, is_solvable

__all__ = [
    "ALL_DIRECTIONS",
    "Arrow",
    "Board",
    "Cell",
    "ClickResult",
    "Direction",
    "Hit",
    "parse_level",
    "TOTAL_LEVELS",
    "Difficulty",
    "difficulty_for",
    "generate_level",
    "find_hint",
    "greedy_solve",
    "is_solvable",
]
