# Card Stats Popup (Anki Add-on)

This add-on shows a small popup after every answered card with:

- Times seen
- Correct vs incorrect distribution
- Ease factor

## Files

- `card_stats_popup/manifest.json`
- `card_stats_popup/__init__.py`

## Install in Anki

1. Open Anki.
2. Go to **Tools -> Add-ons -> View Files**.
3. Create a new folder (for example, `card_stats_popup`).
4. Copy this repository's `card_stats_popup/manifest.json` and `card_stats_popup/__init__.py` into that folder.
5. Restart Anki.

## Behavior

- The popup appears after each answer button press.
- It automatically fades out after a few seconds.
- If a popup already exists, it is replaced by the newest one.

## Notes

- Correct answers are counted as revlog `ease > 1`.
- Incorrect answers are counted as revlog `ease == 1`.
- Ease factor is shown as `card.factor / 10` percent.
