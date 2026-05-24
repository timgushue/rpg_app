from __future__ import annotations

import hashlib

from nicegui import ui

ABILITY_LABELS = {
    "strength": "STR",
    "dexterity": "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom": "WIS",
    "charisma": "CHA",
}


def inject_inkwell_theme() -> None:
    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,600&family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700&family=Public+Sans:wght@400;500;600;700&family=Inter+Tight:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" />
        <link rel="stylesheet" href="/ui_assets/inkwell_styles.css" />
        <script>
        (function () {
          if (window.__rpgClientErrorReporter) return;
          window.__rpgClientErrorReporter = true;
          function report(kind, payload) {
            try {
              fetch('/client-error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({kind: kind, payload: payload, href: window.location.href}),
                keepalive: true
              });
            } catch (_) {}
          }
          window.addEventListener('error', function (event) {
            report('error', {
              message: event.message,
              source: event.filename,
              line: event.lineno,
              column: event.colno,
              stack: event.error && event.error.stack
            });
          });
          window.addEventListener('unhandledrejection', function (event) {
            var reason = event.reason || {};
            report('unhandledrejection', {
              message: reason.message || String(reason),
              stack: reason.stack
            });
          });
        })();
        </script>
        """
    )
    ui.add_css(
        """
        body { background: var(--paper-1, #e8e3da); }
        html, body, #app { width: 100%; height: 100%; min-height: 100%; overflow-x: hidden; }
        .nicegui-content { width: 100% !important; max-width: none !important; padding: 0 !important; }
        .q-layout, .q-page-container, .q-page { width: 100% !important; max-width: none !important; background: transparent !important; padding: 0 !important; }
        .ink-field, .ink-field:focus { box-shadow: none !important; }
        .ink-shell { min-height: 100vh; width: 100%; max-width: none; }
        .ink-link { color: var(--ember-deep); text-decoration: none; }
        .ink-link:hover { text-decoration: underline; }
        .ink-chat-scroll { height: calc(100vh - 270px); min-height: 420px; }
        .ink-sidebar-scroll { max-height: calc(100vh - 180px); }
        .ink-drawer { transition: transform 0.2s ease; }
        .ink-hidden { display: none !important; }
        .ink-overlay-backdrop { background: rgba(36, 24, 14, 0.42); backdrop-filter: blur(2px); }
        .ink-overlay-card { min-width: 360px; max-width: 540px; }
        .ink-card-muted { background: linear-gradient(to bottom, var(--paper-0), var(--paper-1)); }
        .ink-divider { border-top: 1px solid var(--paper-2); }
        .ink-textarea { min-height: 120px; resize: vertical; }
        .ink-screen-limit { width: 100%; max-width: none; margin: 0; }
        .ink-beat p { margin: 0; }
        .ink-beat ul, .ink-beat ol { margin-top: 0.4rem; margin-bottom: 0.4rem; }
        .ink-plain-button { background:none; border:0; padding:0; margin:0; font:inherit; color:inherit; cursor:pointer; }
        .q-btn.ink-btn {
          font-family: var(--ink-display) !important;
          font-size: 16px;
          font-weight: 600;
          padding: 12px 20px;
          border: 1px solid var(--ink-1) !important;
          background: var(--ink-1) !important;
          color: var(--paper-0) !important;
          border-radius: 2px;
          letter-spacing: 0;
          box-shadow: 0 2px 0 oklch(15% 0.02 50);
        }
        .q-btn.ink-btn::before {
          box-shadow: none !important;
        }
        .q-btn.ink-btn.ink-btn-ghost {
          background: transparent !important;
          color: var(--ink-1) !important;
          border-color: var(--ink-2) !important;
          box-shadow: none;
        }
        .q-btn.ink-btn.ink-btn-ember {
          background: var(--ember) !important;
          border-color: var(--ember-deep) !important;
          box-shadow: 0 2px 0 var(--ember-deep);
        }
        """
    )


ICON_PATHS = {
    "menu": '<path d="M3 6h18M3 12h18M3 18h18" />',
    "book": '<path d="M4 4h14a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2V4z" /><path d="M4 4v14a2 2 0 0 0 2 2h14" />',
    "journal": '<path d="M5 3h13a1 1 0 0 1 1 1v17l-3-2-3 2-3-2-3 2V4a1 1 0 0 1 1-1z" />',
    "quill": '<path d="M20 4c-7 1-12 6-14 13l4-1 1 4c7-2 12-7 13-14z" /><path d="M5 19l4-4" />',
    "sword": '<path d="M14 4l6 6-9 9-3-3z" /><path d="M5 17l2 2" />',
    "heart": '<path d="M12 20s-7-4-7-10a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 6-7 10-7 10z" />',
    "coin": '<circle cx="12" cy="12" r="8" /><path d="M9 12h6M12 9v6" />',
    "star": '<path d="M12 3l2.5 6 6.5.5-5 4.5 1.5 6.5L12 17l-5.5 3.5L8 14l-5-4.5 6.5-.5z" />',
    "sparkle": '<path d="M12 4v6M12 14v6M4 12h6M14 12h6M7 7l3 3M14 14l3 3M17 7l-3 3M10 14l-3 3" />',
    "dice": '<rect x="4" y="4" width="16" height="16" rx="2" /><circle cx="9" cy="9" r="1.2" fill="currentColor" stroke="none" /><circle cx="15" cy="15" r="1.2" fill="currentColor" stroke="none" /><circle cx="15" cy="9" r="1.2" fill="currentColor" stroke="none" /><circle cx="9" cy="15" r="1.2" fill="currentColor" stroke="none" />',
    "play": '<path d="M7 4l13 8-13 8z" fill="currentColor" stroke="none" />',
    "pause": '<rect x="6" y="4" width="4" height="16" fill="currentColor" stroke="none" /><rect x="14" y="4" width="4" height="16" fill="currentColor" stroke="none" />',
    "chevron": '<path d="M9 5l7 7-7 7" />',
    "chevronDown": '<path d="M5 9l7 7 7-7" />',
    "pack": '<path d="M7 8V6a5 5 0 0 1 10 0v2M5 8h14l-1 12H6z" />',
    "map": '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" /><path d="M9 3v15M15 6v15" />',
    "scroll": '<path d="M6 4h12c1.5 0 2 1 2 2v3h-3M6 4c-1.5 0-2 1-2 2v12c0 1.5.5 2 2 2h13c-1.5 0-2-.5-2-2v-3h3M6 4c1.5 0 2 1 2 2v12c0 1.5-.5 2-2 2" />',
    "user": '<circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-7 8-7s8 3 8 7" />',
}


def icon_html(name: str, size: int = 16, color: str = "currentColor", stroke: float = 1.7) -> str:
    paths = ICON_PATHS.get(name, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;vertical-align:middle">{paths}</svg>'
    )


def hex_die(value: int, size: int = 36, state_: str = "normal") -> str:
    cls = "ink-die ink-die-d20"
    if state_ == "crit":
        cls += " ink-die-crit"
    elif state_ == "fumble":
        cls += " ink-die-fumble"
    return (
        f'<span class="{cls}" style="width:{size}px;height:{size}px;'
        f'font-size:{int(size * 0.45)}px">{value}</span>'
    )


def ornamental_rule(width: str = "180px") -> str:
    return (
        f'<div class="ink-rule" style="width:{width};margin:0 auto;'
        f'color:var(--ink-3)"><span class="ink-rule-diamond"></span></div>'
    )


def waveform(bars: int = 22, height: int = 14, animated: bool = False) -> str:
    spans = []
    for i in range(bars):
        height_pct = 25 + (int(hashlib.md5(str(i).encode()).hexdigest()[:2], 16) / 255) * 75
        class_attr = ' class="ink-wave-anim"' if animated else ""
        delay = (i % 7) * -0.09
        spans.append(f'<span{class_attr} style="height:{height_pct:.0f}%;animation-delay:{delay:.2f}s"></span>')
    return (
        f'<span class="ink-wave" style="height:{height}px;color:var(--ember-deep)">'
        f'{"".join(spans)}</span>'
    )


def roll_banner_html(roll: dict) -> str:
    degree = roll.get("degree", "").lower()
    failed = degree in {"failure", "critical failure", "fail"}
    die_value = roll.get("roll", 0)
    die_state = "fumble" if failed else ("crit" if die_value == 20 else "normal")
    total_color = "var(--ember)" if failed else "var(--moss)"
    modifier = roll.get("modifier", 0)
    modifier_text = f"+{modifier}" if modifier >= 0 else str(modifier)
    status_text = degree.replace("_", " ") or "resolved"
    return f"""
    <div style="display:grid;grid-template-columns:auto 1fr auto;
                align-items:center;gap:16px;padding:12px 18px;
                background:var(--paper-0);border:1px solid var(--paper-2);
                border-left:3px solid var(--ember-deep);margin-bottom:18px;">
      {hex_die(die_value, 44, die_state)}
      <div>
        <div class="ink-stamp" style="color:var(--ember-deep);font-size:10px">
          {(roll.get('skill') or 'Check')} check · DC {roll.get('dc', 0)} · {status_text}
        </div>
        <div style="font-family:var(--ink-display);font-size:16px;font-weight:600;margin-top:2px">
          d20 <span style="color:var(--ember-deep)">{die_value}</span>
          <span style="color:var(--ink-3);font-weight:400"> {modifier_text} = </span>
          <span style="color:{total_color}">{roll.get('total', 0)}</span>
        </div>
      </div>
      <div class="ink-pill">{status_text}</div>
    </div>
    """
