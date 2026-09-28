#!/usr/bin/env python3
"""Single shareable figure (SVG, 1200x1500) from out/crossnational.json and out/macro.json."""

import argparse
import json
from html import escape
from pathlib import Path

from laya_sim.crossreport import BLUE, GREY, INK, RED, name, summarize

W, H = 1200, 1500
LABELLED = {"TR", "IN", "US", "CN", "DE", "GB", "SK", "VN", "BR", "JP"}


def _text(x, y, s, size=22, weight=400, fill=INK, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>'


def ranked_strip(rows, top, height, focus="TR"):
    """Every country as one column: dot = gap, bar = 95% CI, sorted high to low."""
    rows = sorted(rows, key=lambda r: r["gradient"]["gap"], reverse=True)
    left, right = 110, 40
    lo = min(min(r["gradient"]["low"] for r in rows), -0.02)
    hi = max(r["gradient"]["high"] for r in rows)
    step = (W - left - right) / len(rows)
    sy = lambda v: top + height - (v - lo) / (hi - lo) * height
    out = [f'<line x1="{left}" x2="{W - right}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="{INK}" stroke-width="1.5"/>']
    for tick in (0.1, 0.2):
        out.append(f'<line x1="{left}" x2="{W - right}" y1="{sy(tick):.1f}" y2="{sy(tick):.1f}" stroke="#e5e7eb"/>')
        out.append(_text(left - 12, sy(tick) + 7, f"+{tick * 100:.0f} pp", 20, fill="#6b7280", anchor="end"))
    out.append(_text(left - 12, sy(0) + 7, "0", 20, fill="#6b7280", anchor="end"))
    for i, r in enumerate(rows):
        g, x = r["gradient"], left + (i + 0.5) * step
        is_focus = r["name"] == focus
        color = RED if is_focus else BLUE if g["low"] > 0 else GREY
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{sy(g["low"]):.1f}" y2="{sy(g["high"]):.1f}" stroke="{color}" stroke-width="{4 if is_focus else 2.5}" opacity="{1 if is_focus else 0.45}"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{sy(g["gap"]):.1f}" r="{9 if is_focus else 5}" fill="{color}"/>')
        if r["name"] in LABELLED:
            y = sy(g["high"]) - 14
            out.append(_text(x, y, name(r["name"]), 24 if is_focus else 18, 700 if is_focus else 400,
                             RED if is_focus else "#374151", "middle"))
    return "".join(out)


def mini_scatter(joined, key, label, test, x0, top, w, h, log=False):
    import math
    tx = (lambda v: math.copysign(math.log10(1 + abs(v)), v)) if log else (lambda v: v)
    pts = [(tx(j[key]), j["gap"], j["name"]) for j in joined if j[key] is not None]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    a, b, c, d = min(xs), max(xs), min(ys + [0]), max(ys)
    sx = lambda v: x0 + (v - a) / (b - a) * w
    sy = lambda v: top + h - (v - c) / (d - c) * h
    out = [f'<rect x="{x0 - 16}" y="{top - 70}" width="{w + 32}" height="{h + 110}" rx="16" fill="#f9fafb"/>',
           _text(x0, top - 38, label, 22, 700),
           _text(x0, top - 10, f"r = {test['r']:+.2f}  (p = {test['p']:.2f})", 20, fill="#6b7280"),
           f'<line x1="{x0}" x2="{x0 + w}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="{GREY}" stroke-dasharray="5 5"/>']
    for x, y, code in pts:
        focus = code == "TR"
        out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{8 if focus else 5}" fill="{RED if focus else BLUE}" opacity="{1 if focus else 0.5}"/>')
    out.append(_text(x0 + w / 2, top + h + 30, "worse →" if key != "gdp_growth" else "← worse", 18, fill="#6b7280", anchor="middle"))
    return "".join(out)


def build(result, macro, repo):
    s = summarize(result)
    t = s["focus"]["gradient"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, Helvetica, Arial, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             _text(60, 92, "When money is tight, people want", 52, 800),
             _text(60, 152, "the state to step in. Almost everywhere.", 52, 800),
             _text(60, 206, f'The most economically vulnerable third says "government should take more responsibility"', 24, fill="#4b5563"),
             _text(60, 238, f"more often than the most secure third in {s['positive']} of {s['n']} countries. Reversed in {s['negative']}.", 24, fill="#4b5563"),
             ranked_strip(result["countries"], 300, 520),
             _text(110, 890, f"Each column is a country, sorted by gap. Türkiye: +{t['gap'] * 100:.1f} pp ({t['top_share']:.0%} vs {t['bottom_share']:.0%}), rank {s['focus_rank']} of {s['n']}.", 20, fill="#6b7280"),
             _text(60, 980, "Does a bad national economy make the gap bigger? No detectable link.", 30, 800),
             _text(60, 1016, "Each dot is a country. Height = its gap. Across = the economy around its survey year.", 20, fill="#6b7280")]
    tests = macro["tests"]
    specs = [("unemployment", "Unemployment", False), ("inflation", "Inflation (log)", True), ("gdp_growth", "GDP growth", False)]
    for i, (key, label, log) in enumerate(specs):
        parts.append(mini_scatter(macro["countries"], key, label, tests[key], 76 + i * 370, 1110, 300, 210, log))
    parts += [_text(60, 1420, "The divide tracks where a household stands, not where the national economy is.", 24, 700, fill="#374151"),
              _text(60, 1466, f"Data: Joint EVS/WVS 2017–2022 · World Bank WDI (3-year average to survey year) · 95% bootstrap CIs · {repo}", 17, fill="#9ca3af"),
              "</svg>"]
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="out")
    parser.add_argument("--repo", default="github.com/yigiterturk-dev/laya-wvs-sim")
    args = parser.parse_args()
    out = Path(args.out)
    result = json.loads((out / "crossnational.json").read_text(encoding="utf-8"))
    macro = json.loads((out / "macro.json").read_text(encoding="utf-8"))
    (out / "figure.svg").write_text(build(result, macro, args.repo), encoding="utf-8")
    print(f"wrote {out / 'figure.svg'}")


if __name__ == "__main__":
    main()
