from __future__ import annotations

import json

from aqt.reviewer import Reviewer

from .models import CardStats, PopupSettings


def _ease_emoji(ease_factor_percent: float, correct_pct: int) -> str:
    if correct_pct == 100:
        return "\U0001F680"
    if ease_factor_percent >= 260:
        return "\U0001F680"
    if ease_factor_percent >= 230:
        return "\U0001F642"
    if ease_factor_percent >= 180:
        return "\U0001F610"
    return "\U0001F610"


def show_popup(reviewer: Reviewer, stats: CardStats, settings: PopupSettings) -> None:
    total = max(stats.seen, 1)
    correct_pct = round((stats.correct / total) * 100)
    incorrect_pct = round((stats.incorrect / total) * 100)
    correct_angle = round((stats.correct / total) * 360)
    if stats.correct > 0 and stats.incorrect > 0:
        correct_angle = min(max(correct_angle, 1), 359)
    ease_emoji = _ease_emoji(stats.ease_factor_percent, correct_pct)

    bg = json.dumps(settings.background_color)
    text = json.dumps(settings.text_color)
    good = json.dumps(settings.correct_bar_color)
    bad = json.dumps(settings.incorrect_bar_color)
    duration_ms = settings.duration_ms
    enable_live_picker = "true" if settings.enable_live_color_picker else "false"
    color_row_class = "card-stats-color-row" if settings.enable_live_color_picker else "card-stats-color-row hidden"

    js = f"""
(() => {{
  const existing = document.getElementById('card-stats-popup');
  if (existing) existing.remove();

  const defaultBg = {bg};
  const textColor = {text};
  const goodColor = {good};
  const badColor = {bad};
  const storedBg = localStorage.getItem('cardStatsPopupBg');
  const activeBg = storedBg || defaultBg;
  const savedPos = localStorage.getItem('cardStatsPopupPos');

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const parseRgbString = (value) => {{
    const match = value.match(/rgba?\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (!match) return {{ r: 20, g: 24, b: 28 }};
    return {{
      r: Number(match[1]),
      g: Number(match[2]),
      b: Number(match[3]),
    }};
  }};

  const resolveColor = (value) => {{
    const probe = document.createElement('span');
    probe.style.color = value;
    probe.style.display = 'none';
    document.documentElement.appendChild(probe);
    const resolved = getComputedStyle(probe).color;
    probe.remove();
    return parseRgbString(resolved);
  }};

  const rgbToCss = (rgb) => `rgb(${{rgb.r}}, ${{rgb.g}}, ${{rgb.b}})`;

  const rgbToHsl = (rgb) => {{
    const r = rgb.r / 255;
    const g = rgb.g / 255;
    const b = rgb.b / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const delta = max - min;
    let h = 0;
    let s = 0;
    const l = (max + min) / 2;

    if (delta !== 0) {{
      s = delta / (1 - Math.abs(2 * l - 1));
      if (max === r) h = 60 * (((g - b) / delta) % 6);
      else if (max === g) h = 60 * ((b - r) / delta + 2);
      else h = 60 * ((r - g) / delta + 4);
    }}

    if (h < 0) h += 360;
    return {{ h, s: s * 100, l: l * 100 }};
  }};

  const hslToRgb = (h, s, l) => {{
    const sat = clamp(s, 0, 100) / 100;
    const light = clamp(l, 0, 100) / 100;
    const c = (1 - Math.abs(2 * light - 1)) * sat;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = light - c / 2;
    let r1 = 0;
    let g1 = 0;
    let b1 = 0;

    if (h < 60) {{
      r1 = c;
      g1 = x;
    }} else if (h < 120) {{
      r1 = x;
      g1 = c;
    }} else if (h < 180) {{
      g1 = c;
      b1 = x;
    }} else if (h < 240) {{
      g1 = x;
      b1 = c;
    }} else if (h < 300) {{
      r1 = x;
      b1 = c;
    }} else {{
      r1 = c;
      b1 = x;
    }}

    return {{
      r: Math.round((r1 + m) * 255),
      g: Math.round((g1 + m) * 255),
      b: Math.round((b1 + m) * 255),
    }};
  }};

  const luminance = (rgb) => {{
    const toLinear = (n) => {{
      const x = n / 255;
      return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
    }};
    const r = toLinear(rgb.r);
    const g = toLinear(rgb.g);
    const b = toLinear(rgb.b);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }};

  const contrastRatio = (a, b) => {{
    const l1 = luminance(a);
    const l2 = luminance(b);
    const hi = Math.max(l1, l2);
    const lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }};

  const colorDistance = (a, b) =>
    Math.sqrt((a.r - b.r) ** 2 + (a.g - b.g) ** 2 + (a.b - b.b) ** 2);

  const shiftAwayFromBackground = (candidate, background, hueShift) => {{
    let next = candidate;
    if (colorDistance(next, background) < 95) {{
      const bgHsl = rgbToHsl(background);
      const hue = (bgHsl.h + hueShift) % 360;
      const sat = clamp(Math.max(bgHsl.s, 70), 65, 95);
      const light = bgHsl.l > 55 ? 36 : 62;
      next = hslToRgb(hue, sat, light);
    }}

    if (contrastRatio(next, background) < 1.35) {{
      const hsl = rgbToHsl(next);
      const light = background.r + background.g + background.b > 382 ? 30 : 70;
      next = hslToRgb(hsl.h, clamp(hsl.s + 10, 55, 95), light);
    }}

    return next;
  }};

  const computePalette = (backgroundCss) => {{
    const background = resolveColor(backgroundCss);
    const configuredText = resolveColor(textColor);
    const white = {{ r: 245, g: 247, b: 250 }};
    const dark = {{ r: 20, g: 24, b: 28 }};

    let text = configuredText;
    if (contrastRatio(background, text) < 4.5) {{
      text = contrastRatio(background, white) >= contrastRatio(background, dark) ? white : dark;
    }}

    let correct = shiftAwayFromBackground(resolveColor(goodColor), background, 140);
    let incorrect = shiftAwayFromBackground(resolveColor(badColor), background, 300);

    if (colorDistance(correct, incorrect) < 110) {{
      const bgHsl = rgbToHsl(background);
      correct = hslToRgb((bgHsl.h + 150) % 360, 85, bgHsl.l > 55 ? 36 : 62);
      incorrect = hslToRgb((bgHsl.h + 330) % 360, 85, bgHsl.l > 55 ? 44 : 58);
    }}

    return {{
      text: rgbToCss(text),
      correct: rgbToCss(correct),
      incorrect: rgbToCss(incorrect),
    }};
  }};

  const palette = computePalette(activeBg);

  const toHexColor = (value) => {{
    if (!value) return '#14181c';
    const trimmed = value.trim();
    if (/^#[0-9a-fA-F]{{6}}$/.test(trimmed)) return trimmed;
    if (/^#[0-9a-fA-F]{{3}}$/.test(trimmed)) {{
      return '#' + trimmed.slice(1).split('').map((ch) => ch + ch).join('');
    }}
    return '#14181c';
  }};

  const popup = document.createElement('div');
  popup.id = 'card-stats-popup';
  popup.innerHTML = `
    <div class="card-stats-title">Card Stats</div>
    <div class="card-stats-row"><span>Times seen</span><strong>{stats.seen}</strong></div>
    <div class="card-stats-row"><span>Correct</span><strong>{stats.correct} ({correct_pct}%)</strong></div>
    <div class="card-stats-row"><span>Incorrect</span><strong>{stats.incorrect} ({incorrect_pct}%)</strong></div>
    <div class="card-stats-chart">
      <div class="card-stats-pie" aria-label="Correct vs Incorrect pie chart"></div>
      <div class="card-stats-chart-legend">
        <div class="card-stats-legend-row">
          <span class="card-stats-dot card-stats-dot-correct"></span>
          <span>Correct</span>
          <strong>{stats.correct} ({correct_pct}%)</strong>
        </div>
        <div class="card-stats-legend-row">
          <span class="card-stats-dot card-stats-dot-incorrect"></span>
          <span>Incorrect</span>
          <strong>{stats.incorrect} ({incorrect_pct}%)</strong>
        </div>
      </div>
    </div>
    <div class="card-stats-row"><span>Ease factor</span><strong>{stats.ease_factor_percent:.1f}% {ease_emoji}</strong></div>
    <div class="{color_row_class}">
      <label for="card-stats-color-input">Popup color</label>
      <input id="card-stats-color-input" type="color" value="${{toHexColor(activeBg)}}" />
    </div>
  `;

  let style = document.getElementById('card-stats-popup-style');
  if (!style) {{
    style = document.createElement('style');
    style.id = 'card-stats-popup-style';
    document.head.appendChild(style);
  }}
  style.textContent = `
      #card-stats-popup {{
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 9999;
        width: min(420px, calc(100vw - 24px));
        max-width: 440px;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.15);
        --card-stats-text: ${{palette.text}};
        --card-stats-good: ${{palette.correct}};
        --card-stats-bad: ${{palette.incorrect}};
        background: ${{activeBg}};
        color: var(--card-stats-text);
        box-shadow: 0 8px 24px rgba(0,0,0,0.28);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transform: translateY(-6px);
        opacity: 0;
        animation: cardStatsFadeIn 180ms ease-out forwards;
      }}
      #card-stats-popup .card-stats-title {{
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 10px;
        letter-spacing: 0.02em;
        cursor: move;
        user-select: none;
      }}
      #card-stats-popup .card-stats-row {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        font-size: 14px;
        line-height: 1.5;
      }}
      #card-stats-popup .card-stats-chart {{
        margin: 10px 0;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      #card-stats-popup .card-stats-pie {{
        width: 112px;
        height: 112px;
        border-radius: 50%;
        flex: 0 0 112px;
        background: conic-gradient(var(--card-stats-good) 0deg {correct_angle}deg, var(--card-stats-bad) {correct_angle}deg 360deg);
        border: 1px solid rgba(255,255,255,0.2);
      }}
      #card-stats-popup .card-stats-chart-legend {{
        display: grid;
        gap: 6px;
        width: 100%;
      }}
      #card-stats-popup .card-stats-legend-row {{
        display: grid;
        grid-template-columns: 12px 1fr auto;
        gap: 8px;
        align-items: center;
        font-size: 13px;
      }}
      #card-stats-popup .card-stats-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }}
      #card-stats-popup .card-stats-dot-correct {{
        background: var(--card-stats-good);
      }}
      #card-stats-popup .card-stats-dot-incorrect {{
        background: var(--card-stats-bad);
      }}
      #card-stats-popup .card-stats-row strong {{
        font-weight: 700;
      }}
      #card-stats-popup .card-stats-color-row {{
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
      }}
      #card-stats-popup .card-stats-color-row.hidden {{
        display: none;
      }}
      #card-stats-popup #card-stats-color-input {{
        width: 44px;
        height: 26px;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 6px;
        background: transparent;
        padding: 0;
        cursor: pointer;
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

  document.body.appendChild(popup);

  if (savedPos) {{
    try {{
      const parsed = JSON.parse(savedPos);
      if (typeof parsed.left === 'number' && typeof parsed.top === 'number') {{
        popup.style.left = `${{parsed.left}}px`;
        popup.style.top = `${{parsed.top}}px`;
        popup.style.right = 'auto';
      }}
    }} catch (_err) {{
      // Ignore invalid saved position and use defaults.
    }}
  }}

  const title = popup.querySelector('.card-stats-title');
  if (title) {{
    let dragging = false;
    let offsetX = 0;
    let offsetY = 0;

    title.addEventListener('mousedown', (event) => {{
      dragging = true;
      const rect = popup.getBoundingClientRect();
      offsetX = event.clientX - rect.left;
      offsetY = event.clientY - rect.top;
      popup.style.left = `${{rect.left}}px`;
      popup.style.top = `${{rect.top}}px`;
      popup.style.right = 'auto';
      event.preventDefault();
    }});

    document.addEventListener('mousemove', (event) => {{
      if (!dragging) return;

      const maxLeft = Math.max(0, window.innerWidth - popup.offsetWidth);
      const maxTop = Math.max(0, window.innerHeight - popup.offsetHeight);
      const nextLeft = Math.max(0, Math.min(event.clientX - offsetX, maxLeft));
      const nextTop = Math.max(0, Math.min(event.clientY - offsetY, maxTop));

      popup.style.left = `${{nextLeft}}px`;
      popup.style.top = `${{nextTop}}px`;
    }});

    document.addEventListener('mouseup', () => {{
      if (!dragging) return;
      dragging = false;
      localStorage.setItem(
        'cardStatsPopupPos',
        JSON.stringify({{
          left: popup.offsetLeft,
          top: popup.offsetTop,
        }}),
      );
    }});
  }}

  if ({enable_live_picker}) {{
    const colorInput = popup.querySelector('#card-stats-color-input');
    if (colorInput) {{
      colorInput.addEventListener('input', () => {{
        const next = colorInput.value;
        const nextPalette = computePalette(next);
        popup.style.background = next;
        popup.style.setProperty('--card-stats-text', nextPalette.text);
        popup.style.setProperty('--card-stats-good', nextPalette.correct);
        popup.style.setProperty('--card-stats-bad', nextPalette.incorrect);
        localStorage.setItem('cardStatsPopupBg', next);
      }});
    }}
  }}

  setTimeout(() => {{
    popup.style.animation = 'cardStatsFadeOut 220ms ease-in forwards';
    setTimeout(() => popup.remove(), 220);
  }}, {duration_ms});
}})();
"""

    reviewer.web.eval(js)

