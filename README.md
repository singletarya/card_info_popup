# Anki Card Information Popup (Anki Add-on)

This add-on shows a popup for the current card as soon as you grade it, with:

- Times seen
- Correct vs incorrect distribution
- A correct/incorrect pie chart
- Ease factor
- An ease-factor emoji

## Files

- `card_stats_popup/manifest.json`
- `card_stats_popup/__init__.py`
- `card_stats_popup/config.json`
- `card_stats_popup/models.py`
- `card_stats_popup/settings.py`
- `card_stats_popup/stats.py`
- `card_stats_popup/popup.py`
- `card_stats_popup/hooks.py`

## Install in Anki

1. Open Anki.
2. Go to **Tools -> Add-ons -> View Files**.
3. Create a new folder (for example, `card_stats_popup`).
4. Copy the full `card_stats_popup` folder into that location.
5. Restart Anki.

## Behavior

- The popup appears on the same card you just graded.
- The reviewer waits before advancing, so the popup stays visible on that answered card.
- Press any answer button again during the wait to skip the delay and continue immediately.
- It automatically fades out after a few seconds.
- If a popup already exists, it is replaced by the newest one.
- You can change popup color directly in the popup via the built-in color picker.
- Drag the popup by its title to move it anywhere; its position is remembered.

## Customization

Use **Tools -> Add-ons -> Card Stats Popup -> Config** and edit:

- `popup_background_color` (CSS color)
- `popup_text_color` (CSS color)
- `chart_correct_color` (CSS color)
- `chart_incorrect_color` (CSS color)
- `popup_duration_ms` (milliseconds)
- `answer_delay_ms` (milliseconds, clamped to 5000-10000)
- `enable_live_color_picker` (true/false)

## Notes

- Correct answers are counted as revlog `ease > 1`.
- Incorrect answers are counted as revlog `ease == 1`.
- Ease factor is shown as `card.factor / 10` percent.
