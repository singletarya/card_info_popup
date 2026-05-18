from __future__ import annotations

from dataclasses import dataclass

from aqt import gui_hooks, mw
from aqt.reviewer import Reviewer


@dataclass
class CardStats:
    seen: int
    correct: int
    incorrect: int
    ease_factor_percent: float


def _collect_card_stats(card_id: int, factor: int) -> CardStats:
    # Revlog stores one row per answer; ease=1 is incorrect, ease>1 is correct.
    rows = mw.col.db.all(
        """
        select ease
        from revlog
        where cid = ?
          and ease between 1 and 4
        """,
        card_id,
    )

    seen = len(rows)
    incorrect = sum(1 for (ease,) in rows if ease == 1)
    correct = seen - incorrect
    ease_factor_percent = factor / 10.0

    return CardStats(
        seen=seen,
        correct=correct,
        incorrect=incorrect,
        ease_factor_percent=ease_factor_percent,
    )


def _show_popup(reviewer: Reviewer, stats: CardStats) -> None:
    total = max(stats.seen, 1)
    correct_pct = round((stats.correct / total) * 100)
    incorrect_pct = round((stats.incorrect / total) * 100)

    js = f"""
(() => {{
  const existing = document.getElementById('card-stats-popup');
  if (existing) existing.remove();

  const popup = document.createElement('div');
  popup.id = 'card-stats-popup';
  popup.innerHTML = `
    <div class="card-stats-title">Card Stats</div>
    <div class="card-stats-row"><span>Times seen</span><strong>{stats.seen}</strong></div>
    <div class="card-stats-row"><span>Correct</span><strong>{stats.correct} ({correct_pct}%)</strong></div>
    <div class="card-stats-row"><span>Incorrect</span><strong>{stats.incorrect} ({incorrect_pct}%)</strong></div>
    <div class="card-stats-row"><span>Ease factor</span><strong>{stats.ease_factor_percent:.1f}%</strong></div>
  `;

  const style = document.createElement('style');
  style.id = 'card-stats-popup-style';
  if (!document.getElementById('card-stats-popup-style')) {{
    style.textContent = `
      #card-stats-popup {{
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 9999;
        min-width: 230px;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.15);
        background: rgba(20, 24, 28, 0.92);
        color: #f3f4f6;
        box-shadow: 0 8px 24px rgba(0,0,0,0.28);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transform: translateY(-6px);
        opacity: 0;
        animation: cardStatsFadeIn 180ms ease-out forwards;
      }}
      #card-stats-popup .card-stats-title {{
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: 0.02em;
      }}
      #card-stats-popup .card-stats-row {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        font-size: 12px;
        line-height: 1.6;
      }}
      #card-stats-popup .card-stats-row strong {{
        font-weight: 700;
      }}
      @keyframes cardStatsFadeIn {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
      @keyframes cardStatsFadeOut {{
        to {{
          opacity: 0;
          transform: translateY(-6px);
        }}
      }}
    `;
    document.head.appendChild(style);
  }}

  document.body.appendChild(popup);

  setTimeout(() => {{
    popup.style.animation = 'cardStatsFadeOut 220ms ease-in forwards';
    setTimeout(() => popup.remove(), 220);
  }}, 3200);
}})();
"""

    reviewer.web.eval(js)


def _on_answer_card(reviewer: Reviewer, card, ease: int) -> None:
    # Hook fires after a card is answered; gather stats and render overlay.
    _ = ease
    stats = _collect_card_stats(card.id, card.factor)
    _show_popup(reviewer, stats)


gui_hooks.reviewer_did_answer_card.append(_on_answer_card)
