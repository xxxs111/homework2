"""存档：把通关进度（解锁到第几关、每关几颗星、最好成绩）写到 progress.json。

文件直接放在项目目录下，读写失败（比如目录只读）时静默降级为「本次运行内存存档」，
不影响游戏本身。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict

SAVE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progress.json")


@dataclass
class Progress:
    unlocked: int = 1
    stars: Dict[int, int] = field(default_factory=dict)
    best_time: Dict[int, float] = field(default_factory=dict)
    path: str = SAVE_FILE

    # ------------------------------------------------------------------ 读写

    @classmethod
    def load(cls, path: str = SAVE_FILE) -> "Progress":
        progress = cls(path=path)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            progress.unlocked = max(1, int(data.get("unlocked", 1)))
            progress.stars = {int(k): int(v) for k, v in data.get("stars", {}).items()}
            progress.best_time = {int(k): float(v) for k, v in data.get("best_time", {}).items()}
        except (OSError, ValueError, TypeError):
            pass
        return progress

    def save(self) -> bool:
        data = {
            "unlocked": self.unlocked,
            "stars": {str(k): v for k, v in sorted(self.stars.items())},
            "best_time": {str(k): round(v, 3) for k, v in sorted(self.best_time.items())},
        }
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------ 查询

    def stars_of(self, level: int) -> int:
        return self.stars.get(level, 0)

    def is_unlocked(self, level: int) -> bool:
        return level <= self.unlocked

    def total_stars(self) -> int:
        return sum(self.stars.values())

    # ------------------------------------------------------------------ 更新

    def record(self, level: int, stars: int, seconds: float, total_levels: int) -> None:
        if stars > self.stars.get(level, 0):
            self.stars[level] = stars
        old_best = self.best_time.get(level)
        if old_best is None or seconds < old_best:
            self.best_time[level] = seconds
        if level >= self.unlocked:
            self.unlocked = min(level + 1, total_levels)
        self.save()
