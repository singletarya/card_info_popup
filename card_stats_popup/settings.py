from __future__ import annotations

from .models import PopupSettings


def load_settings() -> PopupSettings:
    # All settings are hardcoded to prevent user modifications via config dialog.
    # Live color picker in the popup allows runtime color changes without config changes.
    return PopupSettings(
        background_color="rgba(20, 24, 28, 0.95)",
        text_color="#f3f4f6",
        correct_bar_color="#2ecc71",
        incorrect_bar_color="#e74c3c",
        duration_ms=8500,
        answer_delay_ms=7000,
        enable_live_color_picker=True,
    )
