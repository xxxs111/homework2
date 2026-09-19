"""一箭又一箭 · 核心规则层。

这一层只描述「棋盘 / 箭头 / 规则」，不 import pygame，也不做任何绘制，
因此可以脱离界面单独跑单元测试（见 ``tests/test_core.py``）。

坐标约定
--------
``x`` 向右、``y`` 向下，``(0, 0)`` 在左上角，与 pygame 屏幕坐标一致。

性能设计
--------
「射线上第一个挡路的是谁」是这类游戏最核心、调用最频繁的查询（悬停预览、
点击判定、关卡生成、提示算法都在用）。为了把它做到 O(1)，棋盘内部为每一行
维护 ``箭头位掩码 / 墙位掩码``，为每一列也维护一份；一次移位 + 取最低位就能
得到最近的障碍物，不需要逐格循环。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Set, Tuple

Cell = Tuple[int, int]


class Direction(Enum):
    """箭头方向。value 是 (dx, dy)，注意屏幕坐标 y 轴向下。"""

    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def label(self) -> str:
        """中文名，用于提示文案与调试输出。"""
        return {"UP": "上", "RIGHT": "右", "DOWN": "下", "LEFT": "左"}[self.name]

    def step(self, cell: Cell) -> Cell:
        """返回沿该方向走一格后的坐标。"""
        return (cell[0] + self.dx, cell[1] + self.dy)


ALL_DIRECTIONS: Tuple[Direction, ...] = (
    Direction.UP,
    Direction.RIGHT,
    Direction.DOWN,
    Direction.LEFT,
)
"""固定顺序的四方向，保证生成器随机取样时结果可复现。"""


def _low_bit(mask: int) -> Optional[int]:
    """最低位 1 的下标；mask 为 0 时返回 None。"""
    if not mask:
        return None
    return (mask & -mask).bit_length() - 1


def _high_bit(mask: int) -> Optional[int]:
    """最高位 1 的下标；mask 为 0 时返回 None。"""
    if not mask:
        return None
    return mask.bit_length() - 1


@dataclass
class Arrow:
    """一个箭头：占一格，带一个方向。

    ``head`` 与 ``cell`` 都返回它所在的格子（保留 ``head`` 这个名字是为了读代码时
    更贴合「箭头头部」的语义）。
    """

    id: int
    x: int
    y: int
    direction: Direction
    color: int = 0

    @property
    def cell(self) -> Cell:
        return (self.x, self.y)

    @property
    def head(self) -> Cell:
        return (self.x, self.y)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"Arrow#{self.id}({self.x},{self.y},{self.direction.name})"


@dataclass(frozen=True)
class Hit:
    """射线扫描结果。

    ``kind``      ``"arrow"`` / ``"wall"`` / ``"edge"``
    ``cell``      撞到的格子；撞到棋盘边缘时为 None
    ``distance``  距离（格）。箭头 / 墙是到该格子的步数；edge 表示飞出棋盘所需步数
    """

    kind: str
    cell: Optional[Cell]
    distance: int


@dataclass
class ClickResult:
    """一次点击的判定结果，界面层据此播放不同动画。"""

    flew: bool
    arrow: Arrow
    hit: Hit
    open_cells: List[Cell]
    blocker: Optional[Arrow] = None

    @property
    def hit_wall(self) -> bool:
        return self.hit.kind == "wall"


class Board:
    """棋盘：尺寸、墙、箭头，以及全部规则判定。"""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("棋盘尺寸必须为正整数")
        if width > 31 or height > 31:
            raise ValueError("位掩码实现只支持 31 以内的边长")
        self.width = width
        self.height = height
        self.arrows: Dict[int, Arrow] = {}
        self.walls: Set[Cell] = set()
        self._next_id = 1
        self._by_cell: Dict[Cell, int] = {}
        # 位掩码：第 i 位为 1 表示该行 / 该列的第 i 格被占用
        self._arrow_row = [0] * height
        self._arrow_col = [0] * width
        self._wall_row = [0] * height
        self._wall_col = [0] * width

    # ------------------------------------------------------------------ 基本查询

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        return (x, y) in self.walls

    def arrow_at(self, x: int, y: int) -> Optional[Arrow]:
        aid = self._by_cell.get((x, y))
        return self.arrows.get(aid) if aid is not None else None

    def is_empty(self, x: int, y: int) -> bool:
        """该格既没有箭头也没有墙（且在图内）。"""
        return self.in_bounds(x, y) and (x, y) not in self.walls and (x, y) not in self._by_cell

    @property
    def arrow_count(self) -> int:
        return len(self.arrows)

    def arrows_list(self) -> List[Arrow]:
        return list(self.arrows.values())

    def free_arrows(self) -> List[Arrow]:
        """当前可以立刻飞出去的箭头。"""
        return [a for a in self.arrows.values() if self.is_free(a)]

    def blocked_arrows(self) -> List[Arrow]:
        """当前被挡住的箭头。"""
        return [a for a in self.arrows.values() if not self.is_free(a)]

    def is_clear(self) -> bool:
        """棋盘上的箭头是否已经全部飞出（过关条件）。"""
        return not self.arrows

    def occupied_cells(self) -> Set[Cell]:
        return set(self._by_cell.keys())

    def empties(self) -> List[Cell]:
        """所有既没有墙也没有箭头的格子。"""
        taken = self.walls | set(self._by_cell.keys())
        return [(x, y)
                for y in range(self.height)
                for x in range(self.width)
                if (x, y) not in taken]

    # ------------------------------------------------------------------ 增删

    def add_arrow(self, x: int, y: int, direction: Direction, color: int = 0) -> Arrow:
        """在 ``(x, y)`` 放一个朝 ``direction`` 的箭头。"""
        if not self.in_bounds(x, y):
            raise ValueError(f"箭头位置越界: {(x, y)}")
        if not self.is_empty(x, y):
            raise ValueError(f"格子已被占用: {(x, y)}")
        arrow = Arrow(self._next_id, x, y, direction, color)
        self._next_id += 1
        self.arrows[arrow.id] = arrow
        self._by_cell[(x, y)] = arrow.id
        self._arrow_row[y] |= 1 << x
        self._arrow_col[x] |= 1 << y
        return arrow

    def add_wall(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise ValueError(f"墙位置越界: {(x, y)}")
        if not self.is_empty(x, y):
            raise ValueError(f"格子已被占用: {(x, y)}")
        self.walls.add((x, y))
        self._wall_row[y] |= 1 << x
        self._wall_col[x] |= 1 << y

    def remove_arrow(self, arrow: "Arrow | int") -> Optional[Arrow]:
        aid = arrow.id if isinstance(arrow, Arrow) else int(arrow)
        target = self.arrows.pop(aid, None)
        if target is None:
            return None
        self._by_cell.pop((target.x, target.y), None)
        self._arrow_row[target.y] &= ~(1 << target.x)
        self._arrow_col[target.x] &= ~(1 << target.y)
        return target

    def clone(self) -> "Board":
        """深拷贝（求解器与「重开本关」都依赖它，避免互相污染状态）。"""
        copy = Board(self.width, self.height)
        for (x, y) in self.walls:
            copy.add_wall(x, y)
        for arrow in self.arrows.values():
            copy.add_arrow(arrow.x, arrow.y, arrow.direction, arrow.color)
        return copy

    # ------------------------------------------------------------------ 射线与规则

    def scan(self, x: int, y: int, direction: Direction) -> Hit:
        """从 (x, y) 沿 direction 扫描，返回第一个箭头 / 墙 / 边缘。"""
        if direction is Direction.RIGHT:
            am = self._arrow_row[y] >> (x + 1)
            wm = self._wall_row[y] >> (x + 1)
            da, dw = _low_bit(am), _low_bit(wm)
            if da is not None and (dw is None or da <= dw):
                return Hit("arrow", (x + 1 + da, y), da + 1)
            if dw is not None:
                return Hit("wall", (x + 1 + dw, y), dw + 1)
            return Hit("edge", None, self.width - x)

        if direction is Direction.LEFT:
            keep = (1 << x) - 1
            am, wm = self._arrow_row[y] & keep, self._wall_row[y] & keep
            da, dw = _high_bit(am), _high_bit(wm)
            if da is not None and (dw is None or da >= dw):
                return Hit("arrow", (da, y), x - da)
            if dw is not None:
                return Hit("wall", (dw, y), x - dw)
            return Hit("edge", None, x + 1)

        if direction is Direction.DOWN:
            am = self._arrow_col[x] >> (y + 1)
            wm = self._wall_col[x] >> (y + 1)
            da, dw = _low_bit(am), _low_bit(wm)
            if da is not None and (dw is None or da <= dw):
                return Hit("arrow", (x, y + 1 + da), da + 1)
            if dw is not None:
                return Hit("wall", (x, y + 1 + dw), dw + 1)
            return Hit("edge", None, self.height - y)

        # Direction.UP
        keep = (1 << y) - 1
        am, wm = self._arrow_col[x] & keep, self._wall_col[x] & keep
        da, dw = _high_bit(am), _high_bit(wm)
        if da is not None and (dw is None or da >= dw):
            return Hit("arrow", (x, da), y - da)
        if dw is not None:
            return Hit("wall", (x, dw), y - dw)
        return Hit("edge", None, y + 1)

    def is_free(self, arrow: Arrow) -> bool:
        """箭头能否直接飞出棋盘（射线上没有箭头也没有墙）。"""
        return self.scan(arrow.x, arrow.y, arrow.direction).kind == "edge"

    def blockers(self, arrow: Arrow) -> List[Arrow]:
        """射线上挡路的全部箭头，按距离由近到远。"""
        result: List[Arrow] = []
        x, y = arrow.x, arrow.y
        while True:
            x += arrow.direction.dx
            y += arrow.direction.dy
            if not self.in_bounds(x, y):
                break
            other = self.arrow_at(x, y)
            if other is not None:
                result.append(other)
        return result

    def ray_cells(self, x: int, y: int, direction: Direction, stop_at_blocker: bool = False) -> List[Cell]:
        """射线经过的格子清单。

        ``stop_at_blocker=False``：一直到棋盘边缘（画飞行动画用）。
        ``stop_at_blocker=True`` ：遇到第一个非空格子就停下，且包含该格子
                                  （画悬停预览、判断弹道用）。
        """
        cells: List[Cell] = []
        cx, cy = x, y
        while True:
            cx += direction.dx
            cy += direction.dy
            if not self.in_bounds(cx, cy):
                break
            cells.append((cx, cy))
            if stop_at_blocker and not self.is_empty(cx, cy):
                break
        return cells

    def exit_steps(self, arrow: Arrow) -> int:
        """箭头从当前格飞出棋盘需要移动的格数。"""
        d = arrow.direction
        if d is Direction.RIGHT:
            return self.width - arrow.x
        if d is Direction.LEFT:
            return arrow.x + 1
        if d is Direction.DOWN:
            return self.height - arrow.y
        return arrow.y + 1

    def click(self, arrow: Arrow) -> ClickResult:
        """点击判定：能飞就飞，不能飞就返回被谁 / 被什么挡住。"""
        hit = self.scan(arrow.x, arrow.y, arrow.direction)
        ray = self.ray_cells(arrow.x, arrow.y, arrow.direction, stop_at_blocker=True)
        if hit.kind == "arrow":
            blocker = self.arrow_at(*hit.cell) if hit.cell else None
            return ClickResult(False, arrow, hit, ray[:-1], blocker)
        if hit.kind == "wall":
            return ClickResult(False, arrow, hit, ray[:-1], None)
        return ClickResult(True, arrow, hit, ray, None)

    def blocking_map(self) -> Dict[int, int]:
        """``箭头 id -> 挡住它的箭头 id``（没被挡住的不出现在结果里）。"""
        result: Dict[int, int] = {}
        for arrow in self.arrows.values():
            hit = self.scan(arrow.x, arrow.y, arrow.direction)
            if hit.kind == "arrow" and hit.cell is not None:
                blocker = self.arrow_at(*hit.cell)
                if blocker is not None:
                    result[arrow.id] = blocker.id
        return result

    # ------------------------------------------------------------------ 调试 / 测试辅助

    def to_text(self) -> str:
        """把棋盘转成文本网格，便于调试与测试断言。

        箭头画 ``^ > v <``，墙画 ``#``，空地画 ``.``。
        """
        chars = {Direction.UP: "^", Direction.RIGHT: ">", Direction.DOWN: "v", Direction.LEFT: "<"}
        rows = []
        for y in range(self.height):
            line = []
            for x in range(self.width):
                if (x, y) in self.walls:
                    line.append("#")
                    continue
                arrow = self.arrow_at(x, y)
                line.append(chars[arrow.direction] if arrow else ".")
            rows.append("".join(line))
        return "\n".join(rows)


_CHAR_TO_DIR = {"^": Direction.UP, ">": Direction.RIGHT, "v": Direction.DOWN, "<": Direction.LEFT}


def parse_level(rows: Sequence[str]) -> Board:
    """用字符画构造棋盘：``^ > v <`` 是箭头，``#`` 是墙，``.`` 是空地。

    主要给单元测试和「手工关卡」用，例如::

        parse_level([
            "..>.",
            ".#..",
            "v..#",
            "....",
        ])
    """
    if not rows:
        raise ValueError("rows 不能为空")
    width = len(rows[0])
    for row in rows:
        if len(row) != width:
            raise ValueError("每行长度必须一致")
    board = Board(width, len(rows))
    color = 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                board.add_wall(x, y)
            elif ch in _CHAR_TO_DIR:
                board.add_arrow(x, y, _CHAR_TO_DIR[ch], color=color)
                color += 1
            elif ch != ".":
                raise ValueError(f"非法字符 {ch!r}")
    return board
