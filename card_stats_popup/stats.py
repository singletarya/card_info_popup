from __future__ import annotations

from typing import Optional

from aqt import mw

from .models import CardStats


def collect_card_stats(card_id: int, factor: int, pending_ease: Optional[int] = None) -> CardStats:
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

    # When called from the pre-answer hook, include the click that just happened.
    if pending_ease in (1, 2, 3, 4):
        seen += 1
        if pending_ease == 1:
            incorrect += 1
        else:
            correct += 1

    ease_factor_percent = factor / 10.0

    return CardStats(
        seen=seen,
        correct=correct,
        incorrect=incorrect,
        ease_factor_percent=ease_factor_percent,
    )
