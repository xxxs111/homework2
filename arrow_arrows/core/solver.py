"""求解器：校验关卡是否可解、给出提示、统计依赖关系。

因为规则是「移除一个箭头永远不会让别的箭头变得更难飞」，所以自由箭头是单调
递增的：只要每一步都点一个当前能飞的箭头，就一定不会把自己卡死。求解器就是
按这个思路做的贪心（每次优先点「能解锁最多箭头」的那个），用来：

1. 生成器自检——生成出来的关卡必须能被求解器清空，否则丢弃重生成；
2. 单元测试——对大量随机关卡断言「一定可解」；
3. 游戏内提示（H 键）。
"""

from __future__ import annotations

from typing import List, Optional

from .model import Arrow, Board


def directly_blocked_count(board: Board, arrow: Arrow) -> int:
    """有多少箭头被 ``arrow`` 直接挡住（即它是那些箭头射线上的第一个障碍）。"""
    count = 0
    for other in board.arrows.values():
        if other.id == arrow.id:
            continue
        hit = board.scan(other.x, other.y, other.direction)
        if hit.kind == "arrow" and hit.cell == arrow.cell:
            count += 1
    return count


def greedy_solve(board: Board, prefer_unlock: bool = True) -> Optional[List[int]]:
    """贪心求解。返回点击顺序（箭头 id 列表）；无解返回 None。

    本游戏的生成器保证至少存在一个自由箭头，所以正常情况下不会返回 None；
    返回 None 只可能出现在「箭头被墙永久堵死」这种异常关卡上。
    """
    work = board.clone()
    order: List[int] = []
    while work.arrow_count:
        frees = work.free_arrows()
        if not frees:
            return None
        if prefer_unlock:
            chosen = max(frees, key=lambda a: (directly_blocked_count(work, a), -a.id))
        else:
            chosen = min(frees, key=lambda a: a.id)
        order.append(chosen.id)
        work.remove_arrow(chosen.id)
    return order


def is_solvable(board: Board) -> bool:
    return greedy_solve(board, prefer_unlock=False) is not None


def find_hint(board: Board) -> Optional[Arrow]:
    """返回一个建议点击的箭头：在所有能飞的箭头里挑「解锁收益最大」的。"""
    frees = board.free_arrows()
    if not frees:
        return None
    return max(frees, key=lambda a: (directly_blocked_count(board, a), a.direction.name))


def unlock_gain(board: Board, arrow: Arrow) -> int:
    """移除该箭头后，会从「被挡住」变成「可以飞」的箭头数量（用于界面提示）。"""
    before = {a.id for a in board.blocked_arrows()}
    shadow = board.clone()
    shadow.remove_arrow(arrow.id)
    after = {a.id for a in shadow.blocked_arrows()}
    return len(before - after)
