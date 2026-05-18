from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CardStats:
    seen: int
    correct: int
    incorrect: int
    ease_factor_percent: float


@dataclass
class PopupSettings:
    background_color: str
    text_color: str
    correct_bar_color: str
    incorrect_bar_color: str
    duration_ms: int
    answer_delay_ms: int
    enable_live_color_picker: bool
