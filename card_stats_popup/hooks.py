from __future__ import annotations

from aqt import gui_hooks
from aqt.qt import QTimer

from .popup import show_popup
from .settings import load_settings
from .stats import collect_card_stats


def _hide_popup_now(reviewer) -> None:
        reviewer.web.eval(
                """
(() => {
    const popup = document.getElementById('card-stats-popup');
    if (popup) {
        popup.remove();
    }
})();
"""
        )


def _resume_delayed_answer(reviewer, close_popup: bool = False) -> None:
    if not getattr(reviewer, "_card_stats_popup_waiting", False):
        return

    timer = getattr(reviewer, "_card_stats_popup_timer", None)
    if timer is not None:
        timer.stop()
        reviewer._card_stats_popup_timer = None

    pending_ease = getattr(reviewer, "_card_stats_popup_pending_ease", None)
    if pending_ease is None:
        reviewer._card_stats_popup_waiting = False
        return

    reviewer._card_stats_popup_waiting = False
    reviewer._card_stats_popup_pending_ease = None
    reviewer._card_stats_popup_bypass_once = True
    try:
        if close_popup:
            _hide_popup_now(reviewer)
        reviewer._answerCard(pending_ease)
    except Exception:
        reviewer._card_stats_popup_bypass_once = False


def _on_will_answer_card(ease_tuple, reviewer, card):
    proceed, ease = ease_tuple

    if getattr(reviewer, "_card_stats_popup_bypass_once", False):
        reviewer._card_stats_popup_bypass_once = False
        return proceed, ease

    if getattr(reviewer, "_card_stats_popup_waiting", False):
        # A second press skips the remaining popup delay immediately.
        _resume_delayed_answer(reviewer, close_popup=True)
        return False, ease

    if proceed:
        settings = load_settings()
        stats = collect_card_stats(card.id, card.factor, pending_ease=ease)

        # Keep popup visible for at least the answer-delay window.
        settings.duration_ms = max(settings.duration_ms, settings.answer_delay_ms + 300)
        show_popup(reviewer, stats, settings)

        reviewer._card_stats_popup_waiting = True
        reviewer._card_stats_popup_pending_ease = ease

        def _resume_answer() -> None:
            _resume_delayed_answer(reviewer)

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(_resume_answer)
        reviewer._card_stats_popup_timer = timer
        timer.start(settings.answer_delay_ms)
        return False, ease

    return proceed, ease


def _on_answer_card_fallback(reviewer, card, ease: int) -> None:
    # Fallback hook for older Anki versions without reviewer_will_answer_card.
    _ = ease
    stats = collect_card_stats(card.id, card.factor)
    settings = load_settings()
    show_popup(reviewer, stats, settings)


def register_hooks() -> None:
    if hasattr(gui_hooks, "reviewer_will_answer_card"):
        gui_hooks.reviewer_will_answer_card.append(_on_will_answer_card)
    else:
        gui_hooks.reviewer_did_answer_card.append(_on_answer_card_fallback)
