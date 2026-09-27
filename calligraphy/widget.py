"""Interactive Jupyter notebook vector player widget for Chinese calligraphy."""

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence, Union

from calligraphy.animation import STYLE_CONFIGS, get_style_config, resolve_style_expansion


def create_vector_player(
    data: Dict[str, Any],
    char_list: Optional[Sequence[str]] = None,
    duration: Optional[float] = None,
    width: int = 420,
    height: int = 420,
    style: Optional[str] = "standard",
    styles: Optional[Sequence[str]] = None,
    expansion: Optional[float] = None,
    title: Optional[str] = None,
    speed: float = 1.0,
):
    """Create an interactive HTML5/SVG vector player widget for Jupyter notebooks."""
    from IPython.display import HTML

    cfg = get_style_config(style, expansion)
    style_label = (style or "custom").upper()
    widget_id = f"callig_player_{uuid.uuid4().hex[:8]}"

    if styles is not None:
        payload_json = json.dumps({"mode": "comparison", "styles": list(styles), "data": data})
        default_title = "MULTI-STYLE SYNCHRONIZED COMPARISON"
        style_label = "MULTI-STYLE"
    else:
        is_multi = char_list is not None or (isinstance(data, dict) and "strokes" not in data)
        if is_multi:
            if char_list is None:
                char_list = list(data.keys())[:2]
            multi_payload = {ch: data[ch] for ch in char_list}
            payload_json = json.dumps({"mode": "multi", "chars": char_list, "data": multi_payload})
            default_title = f"{' '.join(char_list)} · {style_label}"
        else:
            payload_json = json.dumps({"mode": "single", "data": data})
            default_title = f"CALLIGRAPHY STUDY · {style_label}"

    display_title = title if title is not None else default_title

    html_code = f"""
<div id="{widget_id}" style="font-family: Georgia, serif; background: #ded5c5; padding: 18px; border-radius: 6px; width: {width + 36}px; margin: 12px 0; box-sizing: border-box;">
  <div class="canvas-box" style="width: {width}px; height: {height}px; margin: 0 auto; box-shadow: 0 4px 18px rgba(0,0,0,0.12); background: #f7f2e7;"></div>
  <div style="display: flex; align-items: center; gap: 10px; margin-top: 12px; width: {width}px; margin-left: auto; margin-right: auto;">
    <button class="btn-toggle" style="padding: 6px 14px; font-family: inherit; font-size: 13px; border: 1px solid #7d705c; background: #fbf7ee; cursor: pointer; border-radius: 3px; color: #302b28;">Play</button>
    <input class="slider-seek" type="range" min="0" max="6.0" step="0.02" value="0" style="flex: 1; accent-color: #9d3e2d; cursor: pointer;">
    <span class="lbl-clock" style="font-size: 12px; font-variant-numeric: tabular-nums; color: #433b30; min-width: 76px; text-align: right;">0.00 / 0.00s</span>
    <span style="font-size: 10px; letter-spacing: 1px; padding: 2px 6px; background: #ece4d4; border-radius: 2px; color: #6e614f;">{style_label}</span>
  </div>
</div>

<script>
(function() {{
  const root = document.getElementById("{widget_id}");
  if (!root) return;

  const payload = {payload_json};
  const activeCfg = {json.dumps(cfg)};
  const allConfigs = {json.dumps(STYLE_CONFIGS)};
  const canvasBox = root.querySelector(".canvas-box");
  const btn = root.querySelector(".btn-toggle");
  const seek = root.querySelector(".slider-seek");
  const clock = root.querySelector(".lbl-clock");
  const speed = {speed};

  function trace(points, frac) {{
    frac = Math.max(0, Math.min(1, frac));
    let lens = [];
    for (let i = 0; i < points.length - 1; i++) {{
      lens.push(Math.hypot(points[i+1][0] - points[i][0], points[i+1][1] - points[i][1]));
    }}
    let target = lens.reduce((a, b) => a + b, 0) * frac;
    let visited = [points[0]];
    let left = target;
    for (let i = 0; i < lens.length; i++) {{
      if (left >= lens[i]) {{
        visited.push(points[i+1]);
        left -= lens[i];
      }} else {{
        let p = lens[i] ? left / lens[i] : 0;
        visited.push([
          points[i][0] + (points[i+1][0] - points[i][0]) * p,
          points[i][1] + (points[i+1][1] - points[i][1]) * p
        ]);
        break;
      }}
    }}
    let d = 'M ' + visited.map(p => p[0].toFixed(2) + ' ' + p[1].toFixed(2)).join(' L ');
    return {{ d, tip: visited[visited.length - 1] }};
  }}

  let duration = 6.0;
  let schedule = [];

  if (payload.mode === "single" || payload.mode === "comparison") {{
    const strokes = payload.data.strokes;
    const dur_per = 0.55;
    schedule = strokes.map((_, i) => ({{ start: 0.4 + i * (dur_per + 0.15), duration: dur_per }}));
    duration = schedule[schedule.length - 1].start + dur_per + 0.6;
  }} else {{
    let cursor = 0.4;
    schedule = payload.chars.map(ch => {{
      const d = payload.data[ch];
      const dur = 0.45 + 0.14 * d.strokes.length;
      const item = {{ char: ch, data: d, start: cursor, duration: dur }};
      cursor += dur + 0.35;
      return item;
    }});
    duration = cursor + 0.6;
  }}

  seek.max = duration.toFixed(2);

  function render(time) {{
    let defs = [];
    let inner = "";

    if (payload.mode === "single") {{
      const d = payload.data;
      const curExp = activeCfg.expansion;
      const curStrokeW = activeCfg.trace_width;
      const thin = activeCfg.thin_mode;
      const sx = activeCfg.scale[0], sy = activeCfg.scale[1];
      const rot = activeCfg.rotation;

      defs = d.strokes.map((s, i) => `<clipPath id="{widget_id}_c_${{i}}"><path d="${{s}}"/></clipPath>`);
      const marks = d.strokes.map((s, i) => {{
        const info = schedule[i];
        const p = Math.max(0, Math.min(1, (time - info.start) / info.duration));
        if (p <= 0) return "";
        if (p >= 1) {{
          if (thin) {{
            const full = trace(d.medians[i], 1.0);
            return `<g clip-path="url(#{widget_id}_c_${{i}})">
              <path d="${{full.d}}" fill="none" stroke="#22201e" stroke-width="${{curStrokeW}}" stroke-linecap="round" stroke-linejoin="round"/>
            </g>`;
          }}
          if (curExp > 0) return `<path d="${{s}}" fill="#22201e" stroke="#22201e" stroke-width="${{curExp}}" stroke-linejoin="round"/>`;
          return `<path d="${{s}}" fill="#22201e"/>`;
        }}
        const res = trace(d.medians[i], p);
        return `<g clip-path="url(#{widget_id}_c_${{i}})">
          <path d="${{res.d}}" fill="none" stroke="#22201e" stroke-width="${{curStrokeW}}" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="${{res.tip[0]}}" cy="${{res.tip[1]}}" r="34" fill="#161514" opacity="0.2"/>
        </g>`;
      }});

      const rotStr = rot ? `rotate(${{rot}} 540 540) ` : "";
      inner = `<rect x="80" y="80" width="920" height="920" fill="none" stroke="#caa985" stroke-width="2" opacity=".35"/>
      <path d="M 540 80 V 1000 M 80 540 H 1000" stroke="#caa985" stroke-dasharray="10 14" stroke-width="1.5" opacity=".2"/>
      <g transform="translate(140 160) ${{rotStr}}scale(${{sx}} ${{sy}})">
        <g transform="translate(0 900) scale(1 -1)">${{marks.join("")}}</g>
      </g>`;
    }} else if (payload.mode === "comparison") {{
      const d = payload.data;
      const numStyles = payload.styles.length;
      const totalW = Math.max(1000, numStyles * 220);
      const colW = totalW / numStyles;
      const charSize = Math.min(220, colW - 30);
      const colElements = payload.styles.map((st, k) => {{
        const c = allConfigs[st] || activeCfg;
        const curExp = c.expansion;
        const curStrokeW = c.trace_width;
        const thin = c.thin_mode;
        const sx = c.scale[0], sy = c.scale[1];
        const rot = c.rotation;

        const cX = k * colW + (colW - charSize) / 2;
        const cY = 55;
        const marks = d.strokes.map((s, i) => {{
          const mId = `{widget_id}_cmp_${{k}}_${{i}}`;
          defs.push(`<mask id="${{mId}}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280"><path d="${{s}}" fill="white" stroke="white" stroke-width="${{curExp > 0 ? curExp : 0}}"/></mask>`);
          const info = schedule[i];
          const p = Math.max(0, Math.min(1, (time - info.start) / info.duration));
          if (p <= 0) return "";
          if (p >= 1) {{
            if (thin) {{
              const full = trace(d.medians[i], 1.0);
              return `<g mask="url(#${{mId}})">
                <path d="${{full.d}}" fill="none" stroke="#221f1d" stroke-width="${{curStrokeW}}" stroke-linecap="round" stroke-linejoin="round"/>
              </g>`;
            }}
            if (curExp > 0) return `<path d="${{s}}" fill="#221f1d" stroke="#221f1d" stroke-width="${{curExp}}"/>`;
            return `<path d="${{s}}" fill="#221f1d"/>`;
          }}
          const res = trace(d.medians[i], p);
          return `<g mask="url(#${{mId}})">
            <path d="${{res.d}}" fill="none" stroke="#221f1d" stroke-width="${{curStrokeW}}" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${{res.tip[0]}}" cy="${{res.tip[1]}}" r="34" fill="#1a1715" opacity="0.18"/>
          </g>`;
        }});
        const headerX = k * colW + colW / 2;
        const boxX = k * colW + 8;
        const boxW = colW - 16;
        const rotStr = rot ? `rotate(${{rot}} 512 512) ` : "";
        const scX = (charSize / 1024) * (sx / 0.74);
        const scY = (charSize / 1024) * (sy / 0.74);

        return `<rect x="${{boxX}}" y="14" width="${{boxW}}" height="312" fill="none" stroke="#d5c7b0" stroke-width="1.2" rx="4"/>
          <text x="${{headerX}}" y="38" text-anchor="middle" font-family="Georgia,serif" font-size="11" letter-spacing="1" fill="#6d5f4c">${{c.title}}</text>
          <g transform="translate(${{cX}} ${{cY}}) ${{rotStr}}scale(${{scX}} ${{scY}})">
            <g transform="translate(0 900) scale(1 -1)">${{marks.join("")}}</g>
          </g>`;
      }});
      inner = `${{colElements.join("")}}`;
    }} else {{
      const charSize = 240;
      const marginX = 40;
      const gap = 40;
      const elements = schedule.map((item, idx) => {{
        const cX = marginX + idx * (charSize + gap);
        const cY = 50;
        const d = item.data;
        const stDur = item.duration / d.strokes.length;
        const marks = d.strokes.map((outline, sIdx) => {{
          const mId = `{widget_id}_m_${{idx}}_${{sIdx}}`;
          defs.push(`<mask id="${{mId}}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280"><path d="${{outline}}" fill="white" stroke="white" stroke-width="${{activeCfg.expansion > 0 ? activeCfg.expansion : 0}}"/></mask>`);
          const p = Math.max(0, Math.min(1, (time - item.start - sIdx * stDur) / stDur));
          if (p <= 0) return "";
          if (p >= 1) return `<path d="${{outline}}" fill="#221f1d" stroke="#221f1d" stroke-width="${{activeCfg.expansion > 0 ? activeCfg.expansion : 0}}"/>`;
          const res = trace(d.medians[sIdx], p);
          return `<g mask="url(#${{mId}})">
            <path d="${{res.d}}" fill="none" stroke="#221f1d" stroke-width="${{activeCfg.trace_width}}" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${{res.tip[0]}}" cy="${{res.tip[1]}}" r="34" fill="#1a1715" opacity="0.18"/>
          </g>`;
        }});
        return `<g transform="translate(${{cX}} ${{cY}}) scale(${{charSize / 1024}})">
          <g transform="translate(0 900) scale(1 -1)">${{marks.join("")}}</g>
        </g>`;
      }});

      inner = `<rect x="20" y="20" width="1040" height="1040" fill="none" stroke="#d3c5af" stroke-width="1.5"/>
      <text x="30" y="42" font-family="Georgia,serif" font-size="14" letter-spacing="2" fill="#7a6c58">{display_title}</text>
      ${{elements.join("")}}`;
    }}

    let viewBox = "0 0 1080 1080";
    if (payload.mode === "comparison") {{
      const totalW = Math.max(1000, payload.styles.length * 220);
      viewBox = `0 0 ${{totalW}} 340`;
    }} else if (payload.mode === "multi") {{
      viewBox = `0 0 ${{schedule.length * 280 + 80}} 340`;
    }}

    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${{viewBox}}" width="100%" height="100%">
      <defs>
        <linearGradient id="{widget_id}_bg" x2=".8" y2="1"><stop stop-color="#f7f2e7"/><stop offset="1" stop-color="#ede3d1"/></linearGradient>
        ${{defs.join("")}}
      </defs>
      <rect width="100%" height="100%" fill="url(#{widget_id}_bg)"/>
      ${{inner}}
    </svg>`;
  }}

  let currTime = 0, playing = false, lastNow = 0;

  function update() {{
    canvasBox.innerHTML = render(currTime);
    seek.value = currTime.toFixed(2);
    clock.textContent = currTime.toFixed(2) + " / " + duration.toFixed(2) + "s";
    btn.textContent = playing ? "Pause" : (currTime >= duration ? "Replay" : "Play");
  }}

  function step(now) {{
    if (!playing) return;
    if (lastNow) {{
      currTime = Math.min(duration, currTime + ((now - lastNow) / 1000) * speed);
    }}
    lastNow = now;
    if (currTime >= duration) playing = false;
    update();
    if (playing) requestAnimationFrame(step);
  }}

  btn.onclick = function() {{
    if (playing) {{
      playing = false;
      lastNow = 0;
      update();
      return;
    }}
    if (currTime >= duration) currTime = 0;
    playing = true;
    lastNow = 0;
    requestAnimationFrame(step);
    update();
  }};

  seek.oninput = function() {{
    currTime = parseFloat(seek.value);
    lastNow = 0;
    update();
  }};

  update();
}})();
</script>
"""
    return HTML(html_code)


__all__ = ["create_vector_player"]
