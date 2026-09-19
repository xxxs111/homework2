"""音效：全部用代码合成，不依赖任何音频素材文件。

用 ``array`` 生成 16 位双声道 PCM，直接塞给 ``pygame.mixer.Sound(buffer=...)``。
好处是交作业时只有一个 .py 文件，不会出现「音效文件找不到」的问题；坏处是音色
比较电子，但作为点击反馈足够了。音频初始化失败（比如没有声卡）时自动静音。
"""

from __future__ import annotations

import array
import math
from typing import Dict, Optional, Sequence, Tuple

import pygame

SAMPLE_RATE = 44100


def _render(notes: Sequence[Tuple[float, float, float, str]], volume: float = 0.22) -> bytes:
    """把若干 ``(起始频率, 结束频率, 时长秒, 波形)`` 依次渲染成 PCM。

    波形支持 ``sine``（正弦，圆润）和 ``square``（方波，刺耳，适合「撞墙」）。
    """
    buffer = array.array("h")
    for freq_start, freq_end, seconds, wave in notes:
        count = max(1, int(SAMPLE_RATE * seconds))
        phase = 0.0
        for i in range(count):
            t = i / count
            freq = freq_start + (freq_end - freq_start) * t
            phase += 2 * math.pi * freq / SAMPLE_RATE
            env = (1.0 - t) ** 1.6          # 指数衰减，听感更自然
            if wave == "square":
                value = 1.0 if math.sin(phase) >= 0 else -1.0
            else:
                value = math.sin(phase)
            sample = int(32767 * volume * env * value)
            buffer.append(sample)
            buffer.append(sample)           # 双声道
    return buffer.tobytes()


class Audio:
    """一个极简的音效播放器。"""

    RECIPES: Dict[str, Tuple[Sequence[Tuple[float, float, float, str]], float]] = {
        # 飞出去：上滑的「咻」
        "fly": ([(620, 1500, 0.16, "sine")], 0.20),
        # 被挡住：下滑的方波「咚」
        "blocked": ([(210, 110, 0.26, "square")], 0.16),
        # 点空：很轻的咔哒
        "click": ([(900, 700, 0.05, "sine")], 0.14),
        # 提示：两个短音
        "hint": ([(880, 880, 0.07, "sine"), (1180, 1180, 0.09, "sine")], 0.16),
        # 过关：上行琶音
        "win": ([(523, 523, 0.11, "sine"), (659, 659, 0.11, "sine"),
                 (784, 784, 0.11, "sine"), (1047, 1047, 0.22, "sine")], 0.20),
        # 失败：下行三音
        "lose": ([(440, 440, 0.14, "sine"), (349, 349, 0.14, "sine"), (262, 262, 0.3, "sine")], 0.18),
    }

    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 2, 512)
            self.enabled = True
        except pygame.error:
            return
        for name, (notes, volume) in self.RECIPES.items():
            try:
                self.sounds[name] = pygame.mixer.Sound(buffer=_render(notes, volume))
            except pygame.error:      # pragma: no cover - 依赖具体音频后端
                self.enabled = False
                return

    def play(self, name: str) -> Optional[pygame.mixer.Channel]:
        if not self.enabled or self.muted:
            return None
        sound = self.sounds.get(name)
        if sound is None:
            return None
        return sound.play()

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted
