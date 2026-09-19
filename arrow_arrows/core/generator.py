"""关卡生成器：用「逆向走廊构造法」保证生成出来的关卡一定可解。

为什么一定可解
--------------
设正确点击顺序为 ``r1, r2, ..., rn``（``r1`` 最先被点）。点到 ``ri`` 时场上还剩
``ri, r(i+1), ..., rn``，所以 ``ri`` 的射线上不能有这些**更晚被点掉**的箭头；
至于已经被点掉的 ``r1..r(i-1)`` 出现在它的射线上完全没关系。

于是只要保证：**每放置一个新箭头时，它头前方的射线上没有已经放好的箭头、也没有墙**，
那么「按放置顺序倒着点」就一定是一组合法解——

* 合法性：旧箭头不会出现在新箭头头前方的射线上，所以倒序点击时，新箭头（先被点掉）
  不会挡着旧箭头；
* 可解性：某个箭头放到棋盘上时前方射线是空的，之后只有**更晚放**的箭头可能落进它的
  射线，而这些箭头在倒序里排在它前面、先被点掉，所以轮到它时射线一定又是空的。

走廊策略
--------
只满足上面的约束还不够好玩：随手乱放会放出一大堆「前方空空、随时能点」的箭头。
所以这里改成**一条走廊一条走廊地铺**：

    随机找一个空格和一个方向当走廊起点
      → 沿这个方向放一个箭头（头前方必须一路空到棋盘边缘）
      → 紧接着在它头前方那一格起下一个箭头，方向优先拐 90°（其余概率直行）
      → 重复，直到这条走廊再也铺不动

同一条走廊上，每个箭头都被紧挨着它的下一个箭头挡住，只有走廊末端那一个能直接飞出去，
所以**自由箭头数量 ≈ 走廊条数**，走廊越长谜题越难。走廊会自然拐弯，画面上就是
原游戏那种由彩色箭头串起来的迷宫。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .model import ALL_DIRECTIONS, Board, Cell, Direction
from .solver import greedy_solve

TOTAL_LEVELS = 30
"""游戏内置关卡数量（每关随机生成、可无限重玩）。"""

PALETTE_SIZE = 9
"""界面层调色板大小，生成器按它给箭头分配颜色。"""

_OPPOSITE = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


@dataclass(frozen=True)
class Difficulty:
    """一关的生成参数。"""

    level: int
    size: int        # 棋盘边长
    walls: int       # 墙格数量
    arrows: int      # 目标箭头数量（铺不下就提前停）
    chain_len: int   # 单条走廊最多几个箭头；越少 → 走廊越多 → 自由箭头越多 → 越简单
    max_free: int    # 开局自由箭头的可接受上限（用于挑最好的一次生成结果）
    attempts: int = 5


_SATURATION = {4: 0.95, 5: 0.80, 6: 0.70, 7: 0.62, 8: 0.60, 9: 0.56, 10: 0.52}
"""不同边长下走廊法铺满时能占到的格子比例（小棋盘几乎能铺满，越大越难铺满）。"""

_DENSITY_FACTOR = 0.92
"""目标密度占「铺满」的比例。留一点余量：铺到接近满盘时走廊会被切得很碎，
开局能直接点的箭头数量会反弹。"""


def difficulty_for(level: int) -> Difficulty:
    """难度曲线：棋盘变大、墙变多、走廊变长（自由箭头变少）。

    目标箭头数取 ``4 + 1.9×关卡`` 与「该尺寸铺满后大约能放几条」的较小值，
    保证难度随关卡单调上升，又不会出现「目标根本放不下」而白白重试。

    ============  ======  ====  ======  ========  ========
    关卡           边长   墙    目标    走廊上限  自由上限
    ============  ======  ====  ======  ========  ========
    1              4      0     5        3        6
    5              6      1    13        6        6
    10             8      4    22        9        5
    20            10      8    28       15        4
    30            10      8    28       20        4
    ============  ======  ====  ======  ========  ========
    """
    level = max(1, int(level))
    size = min(4 + (level - 1) // 2, 10)
    cells = size * size
    wall_ratio = 0.0 if level < 4 else min(0.04 + 0.006 * (level - 4), 0.08)
    walls = int(cells * wall_ratio)
    capacity = int((cells - walls) * _SATURATION[size] * _DENSITY_FACTOR)
    arrows = max(4, min(int(4 + 1.9 * level), capacity))
    chain_len = int(min(3 + 0.6 * level, 20))
    max_free = max(4, 6 - level // 8)
    return Difficulty(
        level=level,
        size=size,
        walls=walls,
        arrows=arrows,
        chain_len=chain_len,
        max_free=max_free,
    )


# ---------------------------------------------------------------------------- 墙


def _carve_walls(board: Board, count: int, rng: random.Random, max_len: int = 3) -> None:
    """撒几条随机走向的短墙段，让棋盘有点迷宫味（墙会挡住弹道，所以必须先放）。"""
    if count <= 0:
        return
    placed = 0
    for _ in range(count * 40):
        if placed >= count:
            break
        x = rng.randrange(board.width)
        y = rng.randrange(board.height)
        direction = rng.choice(ALL_DIRECTIONS)
        length = rng.randint(2, max_len)
        segment: List[Cell] = []
        for i in range(length):
            cx, cy = x + direction.dx * i, y + direction.dy * i
            if not board.is_empty(cx, cy):
                break
            segment.append((cx, cy))
        if len(segment) < 2:
            continue
        for (cx, cy) in segment:
            board.add_wall(cx, cy)
        placed += len(segment)


# ---------------------------------------------------------------------------- 走廊


def _ray_to_edge(board: Board, cell: Cell, direction: Direction) -> Optional[int]:
    """``cell`` 沿 ``direction`` 一直到棋盘边缘是否全是空地？

    是则返回这条射线上可用格数（含 ``cell`` 自身），否则返回 ``None``。

    为什么必须一路空到边缘：箭头飞出去靠的是**头前方那条射线**没有别的箭头和墙。
    如果身体只占前几格、把「这里空着」当成可放，那么射线尽头若有别的箭头，
    新箭头一放下去就被永久堵死了——这是多格箭头版本最容易踩的坑（实测直接导致
    生成出来的关卡不可解）。
    """
    hit = board.scan(cell[0], cell[1], direction)
    return hit.distance if hit.kind == "edge" else None


def _next_direction(
    board: Board,
    pos: Cell,
    current: Direction,
    rng: random.Random,
) -> Optional[Direction]:
    """在 ``pos`` 处给下一条箭头挑方向：优先拐 90°，其余情况直行。

    不能往回指（``_OPPOSITE``），否则新箭头头前方立刻就是上一条箭头的头，属于自堵。
    每个候选方向都要求「到边缘一路全空，且至少还剩 2 格」：1 格给箭头身体、
    1 格留给它头前方的余地。
    """
    def usable(direction: Direction) -> bool:
        run = _ray_to_edge(board, pos, direction)
        return run is not None and run >= 2

    candidates = [d for d in ALL_DIRECTIONS if d is not _OPPOSITE[current] and usable(d)]
    if not candidates:
        return None
    if rng.random() < 0.65:
        turns = [d for d in candidates if d is not current]
        if turns:
            return rng.choice(turns)
    return rng.choice(candidates)


def _usable_directions(board: Board, cell: Cell, minimum: int = 2) -> List[Direction]:
    """``cell`` 上哪些方向可以起一条新箭头（一路空到边缘，且至少 ``minimum`` 格）。"""
    result: List[Direction] = []
    for direction in ALL_DIRECTIONS:
        run = _ray_to_edge(board, cell, direction)
        if run is not None and run >= minimum:
            result.append(direction)
    return result


def _carve_chain_from(
    board: Board,
    start: Cell,
    direction: Direction,
    rng: random.Random,
    max_arrows: int,
) -> int:
    """从 ``start`` 出发沿走廊一格一格往前摆箭头，返回本次放了几个（0 表示放不下）。

    走廊上每个箭头都朝向「下一个箭头所在的那一格」，于是它被下一个箭头挡住；
    只有走廊末端那个箭头前方是空的，也就是这条走廊上唯一能直接点的箭头。
    """
    pos, d = start, direction
    placed = 0
    while placed < max_arrows:
        run = _ray_to_edge(board, pos, d)
        if run is None or run < 2:
            # 前方不足两格就没必要放了：至少留一格给自己、一格给头前方
            break
        board.add_arrow(pos[0], pos[1], d, color=rng.randrange(PALETTE_SIZE))
        placed += 1

        nxt = (pos[0] + d.dx, pos[1] + d.dy)
        nxt_direction = _next_direction(board, nxt, d, rng)
        if nxt_direction is None:
            break
        pos, d = nxt, nxt_direction
    return placed


def _carve_chain(board: Board, rng: random.Random, max_arrows: int) -> int:
    """起一条新走廊，返回本次放下的箭头数量（0 表示已经铺不下了）。

    起点的挑法很讲究：遍历所有空格，按「最长可用射线」排序，在前几名里随机挑一个。
    箭头要求「头前方一路空到边缘」，所以射线越长的位置越适合起走廊——而这些位置
    恰恰在棋盘中间。如果只随机抽几个空格试，走廊会全部挤在边上、中间留一大片空地
    （这是实测对比参考图时发现的问题）。
    """
    empties = board.empties()
    if not empties:
        return 0
    rng.shuffle(empties)

    candidates: List[Tuple[int, Cell, List[Direction]]] = []
    for start in empties:
        directions = _usable_directions(board, start)
        if not directions:
            continue
        longest = max(_ray_to_edge(board, start, d) or 0 for d in directions)
        candidates.append((longest, start, directions))
    if not candidates:
        return 0

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, start, directions = rng.choice(candidates[:5])
    return _carve_chain_from(board, start, rng.choice(directions), rng, max_arrows)


def _build(diff: Difficulty, rng: random.Random) -> Board:
    """一条走廊一条走廊地铺，直到放够目标数量或者棋盘再也铺不下。"""
    board = Board(diff.size, diff.size)
    _carve_walls(board, diff.walls, rng)
    guard = diff.arrows * 3 + 12
    while board.arrow_count < diff.arrows and guard > 0:
        guard -= 1
        remaining = diff.arrows - board.arrow_count
        if _carve_chain(board, rng, min(diff.chain_len, remaining)) == 0:
            break
    return board


def generate_level(level: int, rng: Optional[random.Random] = None) -> Board:
    """生成第 ``level`` 关。

    重试若干次，取「开局自由箭头少、箭头数量多」的那张棋盘。
    返回的棋盘一定满足：存在一种点击顺序能把所有箭头清空。
    """
    rng = rng or random.Random()
    diff = difficulty_for(level)
    best: Optional[Board] = None
    best_key: Optional[Tuple[int, int, int]] = None

    for _ in range(diff.attempts):
        board = _build(diff, rng)
        if board.arrow_count == 0:
            continue
        if greedy_solve(board, prefer_unlock=False) is None:
            continue  # 理论上不会发生，作为最后一道保险
        free = len(board.free_arrows())
        ok = free <= diff.max_free and board.arrow_count >= diff.arrows * 0.8
        key = (0 if ok else 1, free, -board.arrow_count)
        if best_key is None or key < best_key:
            best, best_key = board, key
        if ok:
            break

    if best is None:  # 极端保险：至少给一个能玩的小关卡
        best = Board(4, 4)
        best.add_arrow(0, 0, Direction.RIGHT, color=0)
    return best


def difficulty_table(levels: Iterable[int] = range(1, TOTAL_LEVELS + 1)) -> str:
    """把难度曲线打成表，方便写报告 / 调参。"""
    lines = ["关卡  边长  墙  目标箭头  走廊上限  自由上限"]
    for level in levels:
        d = difficulty_for(level)
        lines.append(
            f"{d.level:>4}  {d.size:>4}  {d.walls:>2}  {d.arrows:>8}  "
            f"{d.chain_len:>8}  {d.max_free:>8}"
        )
    return "\n".join(lines)
