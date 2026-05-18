from __future__ import annotations

from aqt import mw

from .models import PopupSettings


def _addon_name() -> str:
    return mw.addonManager.addonFromModule(__name__)


def load_settings() -> PopupSettings:
    cfg = mw.addonManager.getConfig(_addon_name()) or {}

    try:
        duration_ms = int(cfg.get("popup_duration_ms", 3600))
    except (TypeError, ValueError):
        duration_ms = 3600

    try:
        answer_delay_ms = int(cfg.get("answer_delay_ms", 7000))
    except (TypeError, ValueError):
        answer_delay_ms = 7000

    answer_delay_ms = min(max(answer_delay_ms, 5000), 10000)

    return PopupSettings(
        background_color=str(cfg.get("popup_background_color", "rgba(20, 24, 28, 0.95)")),
        text_color=str(cfg.get("popup_text_color", "#f3f4f6")),
        correct_bar_color=str(cfg.get("chart_correct_color", "#2ecc71")),
        incorrect_bar_color=str(cfg.get("chart_incorrect_color", "#e74c3c")),
        duration_ms=max(1200, duration_ms),
        answer_delay_ms=answer_delay_ms,
        enable_live_color_picker=bool(cfg.get("enable_live_color_picker", True)),
    )
