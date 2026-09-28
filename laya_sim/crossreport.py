"""HTML report for the cross-national study (inline SVG, no external requests)."""

from html import escape
from statistics import correlation

NAMES = {
    "AD": "Andorra", "AL": "Albania", "AM": "Armenia", "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "AZ": "Azerbaijan", "BA": "Bosnia & Herz.", "BD": "Bangladesh", "BG": "Bulgaria", "BO": "Bolivia",
    "BR": "Brazil", "BY": "Belarus", "CA": "Canada", "CH": "Switzerland", "CL": "Chile", "CN": "China",
    "CO": "Colombia", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EC": "Ecuador",
    "EE": "Estonia", "EG": "Egypt", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FR": "France",
    "GB": "Great Britain", "GE": "Georgia", "GR": "Greece", "GT": "Guatemala", "HK": "Hong Kong", "HR": "Croatia",
    "HU": "Hungary", "ID": "Indonesia", "IN": "India", "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy",
    "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan", "KR": "South Korea", "KZ": "Kazakhstan",
    "LB": "Lebanon", "LT": "Lithuania", "LV": "Latvia", "LY": "Libya", "MA": "Morocco", "ME": "Montenegro",
    "MK": "North Macedonia", "MM": "Myanmar", "MN": "Mongolia", "MO": "Macao", "MV": "Maldives", "MX": "Mexico",
    "MY": "Malaysia", "NG": "Nigeria", "NI": "Nicaragua", "NIR": "Northern Ireland", "NL": "Netherlands",
    "NO": "Norway", "NZ": "New Zealand", "PE": "Peru", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "PR": "Puerto Rico", "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "RU": "Russia", "SE": "Sweden",
    "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia", "TH": "Thailand", "TJ": "Tajikistan", "TN": "Tunisia",
    "TR": "Türkiye", "TW": "Taiwan", "UA": "Ukraine", "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VE": "Venezuela", "VN": "Vietnam", "ZW": "Zimbabwe",
}
BLUE, RED, GREY, INK = "#2563eb", "#dc2626", "#9ca3af", "#111827"


def name(code):
    return NAMES.get(code, code)


def _pp(value):
    return f"{value * 100:+.1f}"


def _dot_plot(rows, key, focus="TR"):
    rows = sorted(rows, key=lambda r: r[key]["gap"], reverse=True)
    row_h, width, left, right, top = 15, 640, 128, 20, 24
    height = top + row_h * len(rows) + 28
    lo = min(min(r[key]["low"] for r in rows), 0)
    hi = max(r[key]["high"] for r in rows)
    x = lambda v: left + (v - lo) / (hi - lo) * (width - left - right)
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Vulnerability gap by country">',
           f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{top - 6}" y2="{height - 26}" stroke="{GREY}"/>']
    for tick in (0, 0.1, 0.2):
        if lo <= tick <= hi:
            out.append(f'<text x="{x(tick):.1f}" y="{top - 10}" text-anchor="middle">{_pp(tick)} pp</text>')
    for i, r in enumerate(rows):
        y = top + i * row_h + row_h / 2
        g = r[key]
        is_focus = r["name"] == focus
        significant = g["low"] > 0
        color = RED if is_focus else BLUE if significant else GREY
        weight = ' font-weight="700"' if is_focus else ""
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end"{weight} fill="{color if is_focus else INK}">{escape(name(r["name"]))}</text>')
        out.append(f'<line x1="{x(g["low"]):.1f}" x2="{x(g["high"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="{2.5 if is_focus else 1.5}" opacity="0.8"/>')
        out.append(f'<circle cx="{x(g["gap"]):.1f}" cy="{y:.1f}" r="{4.5 if is_focus else 3}" fill="{color}"/>')
    out.append(f'<text x="{(left + width) / 2}" y="{height - 6}" text-anchor="middle">gap in "government should take more responsibility" (most minus least vulnerable third)</text></svg>')
    return "".join(out)


def _scatter(rows, focus="TR"):
    width, height, pad = 560, 360, 52
    xs = [r["gradient"]["gap"] for r in rows]
    ys = [r["drift"]["structure"]["mean"] for r in rows]
    x0, x1 = min(xs + [0]), max(xs)
    y0, y1 = min(ys + [0]), max(ys + [0])
    sx = lambda v: pad + (v - x0) / (x1 - x0) * (width - 2 * pad)
    sy = lambda v: height - pad - (v - y0) / ((y1 - y0) or 1) * (height - 2 * pad)
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Gap versus structure effect">',
           f'<line x1="{pad}" x2="{width - pad}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="{GREY}" stroke-dasharray="4 4"/>',
           f'<line x1="{sx(0):.1f}" x2="{sx(0):.1f}" y1="{pad}" y2="{height - pad}" stroke="{GREY}" stroke-dasharray="4 4"/>']
    for r, xv, yv in zip(rows, xs, ys):
        is_focus = r["name"] == focus
        out.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(yv):.1f}" r="{6 if is_focus else 3.5}" fill="{RED if is_focus else BLUE}" opacity="{1 if is_focus else 0.55}"><title>{escape(name(r["name"]))}</title></circle>')
        if is_focus or abs(xv) > 0.19 or xv < -0.02:
            out.append(f'<text x="{sx(xv) + 7:.1f}" y="{sy(yv) + 4:.1f}"{" font-weight=700" if is_focus else ""}>{escape(name(r["name"]))}</text>')
    out.append(f'<text x="{width / 2}" y="{height - 12}" text-anchor="middle">observed gap (pp, survey data)</text>')
    out.append(f'<text x="14" y="{height / 2}" transform="rotate(-90 14 {height / 2})" text-anchor="middle">simulated structure effect</text>')
    out.append(f'<text x="{pad}" y="{height - pad + 16}">{_pp(x0)}</text><text x="{width - pad}" y="{height - pad + 16}" text-anchor="end">{_pp(x1)}</text>')
    out.append(f'<text x="{pad - 6}" y="{sy(y1) + 4:.1f}" text-anchor="end">{y1:+.3f}</text><text x="{pad - 6}" y="{sy(y0) + 4:.1f}" text-anchor="end">{y0:+.3f}</text></svg>')
    return "".join(out)


def summarize(result, focus="TR"):
    rows = result["countries"]
    ranked = sorted(rows, key=lambda r: r["gradient"]["gap"], reverse=True)
    inc = [r["gradient_income_only"] for r in rows]
    structure = [r["drift"]["structure"] for r in rows]
    focus_row = next(r for r in rows if r["name"] == focus)
    return {
        "n": len(rows),
        "positive": sum(r["gradient"]["low"] > 0 for r in rows),
        "negative": sum(r["gradient"]["high"] < 0 for r in rows),
        "income_positive": sum(g["low"] > 0 for g in inc),
        "income_negative": sum(g["high"] < 0 for g in inc),
        "median_gap": sorted(r["gradient"]["gap"] for r in rows)[len(rows) // 2],
        "structure_negative": sum(s["high"] < 0 for s in structure),
        "structure_positive": sum(s["low"] > 0 for s in structure),
        "corr_gap_structure": correlation([r["gradient"]["gap"] for r in rows], [s["mean"] for s in structure]),
        "focus": focus_row,
        "focus_rank": ranked.index(focus_row) + 1,
        "top5": [name(r["name"]) for r in ranked[:5]],
        "bottom5": [name(r["name"]) for r in ranked[-5:]],
    }


def build_html(result, source_name):
    s = summarize(result)
    t = s["focus"]
    g, gi, d = t["gradient"], t["gradient_income_only"], t["drift"]
    design = result["design"]
    skipped = ", ".join(name(c) for c in result["skipped"])
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Who wants the state to step in? 87 countries</title><style>
body{{margin:0;background:#fff;color:{INK};font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:36px 20px 72px}}h1{{font-size:30px;line-height:1.2;margin:0 0 10px}}h2{{margin-top:44px;font-size:20px}}
.lede{{color:#4b5563;font-size:17px}}.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));gap:12px;margin:24px 0}}
.stat{{border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px}}.stat b{{display:block;font-size:28px;line-height:1.1}}.stat span{{color:#6b7280;font-size:13px}}
.panel{{border:1px solid #e5e7eb;border-radius:12px;padding:14px}}svg{{width:100%;height:auto;font-size:11px;fill:#374151}}
.note{{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:12px 16px}}.small{{color:#6b7280;font-size:13px}}code{{background:#f3f4f6;padding:1px 5px;border-radius:4px}}
.key span{{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 5px 0 14px}}</style></head><body><main>
<h1>When money is tight, do people want the state to step in?</h1>
<p class=lede>Survey evidence from {s['n']} countries (Joint EVS/WVS 2017–2022), followed by a simulation of what that structure means for a crisis scenario.</p>
<div class=stats>
<div class=stat><b>{s['positive']}/{s['n']}</b><span>countries where the most economically vulnerable third is significantly more likely to say "government should take more responsibility"</span></div>
<div class=stat><b>{s['negative']}</b><span>countries where the pattern significantly reverses</span></div>
<div class=stat><b>{_pp(g['gap'])} pp</b><span>gap in Türkiye ({g['top_share']:.0%} vs {g['bottom_share']:.0%}); rank {s['focus_rank']} of {s['n']}</span></div>
<div class=stat><b>{_pp(s['median_gap'])} pp</b><span>median gap across countries</span></div></div>

<h2>1. The survey pattern (no model involved)</h2>
<p>For each country, respondents are split into thirds by a vulnerability score (low household income step, unemployment, low life satisfaction), using the country's own weighted terciles.
Each row shows how much more often the most vulnerable third answers 7–10 on E037 ("the government should take more responsibility to ensure everyone is provided for") than the least vulnerable third, with a 95% respondent-bootstrap CI.</p>
<p class="small key"><span style="background:{BLUE}"></span>CI above zero<span style="background:{GREY}"></span>not distinguishable from zero<span style="background:{RED}"></span>Türkiye</p>
<div class=panel>{_dot_plot(result['countries'], 'gradient')}</div>
<p><strong>Largest gaps:</strong> {', '.join(s['top5'])}. <strong>Smallest:</strong> {', '.join(s['bottom5'])}.</p>
<p><strong>Robustness.</strong> Splitting by household income alone, instead of the composite score, still gives a significant positive gap in {s['income_positive']} of {s['n']} countries and a significant reversal in {s['income_negative']}.
In Türkiye the income-only gap is {_pp(gi['gap'])} pp [{_pp(gi['low'])}, {_pp(gi['high'])}].</p>

<h2>2. What that structure does in a simulated crisis</h2>
<p>Every country runs the same agent-based model: {design['agents']:,} agents sampled by survey weight, {design['rounds']} rounds, {len(design['seeds'])} seeds.
The crisis assumption ("drift", strength {design['drift_strength']}) nudges economically vulnerable agents toward "government responsible".
The same model then runs on a placebo in which every attribute is shuffled independently, which keeps each variable's distribution and removes who-is-who.
The <em>structure effect</em> is the real result minus the placebo result: the part of the simulated shift that comes from how vulnerability and attitudes actually co-occur in that country.</p>
<div class=panel>{_scatter(result['countries'])}</div>
<p>Correlation between the observed gap and the structure effect: <strong>{s['corr_gap_structure']:+.2f}</strong>. The structure effect is significantly negative in {s['structure_negative']} of {s['n']} countries and significantly positive in {s['structure_positive']}.
<strong>This is a weak result.</strong> The expected ceiling effect (the vulnerable already lean toward state responsibility, so a crisis pushing them further has less room to act) points in the right direction, but in most countries the model cannot distinguish it from the placebo.
In this model the mechanism, not the real data structure, drives most of the simulated shift.</p>
<p>Türkiye: simulated shift {d['real']['mean']:+.3f} [{d['real']['low']:+.3f}, {d['real']['high']:+.3f}] vs placebo {d['placebo']['mean']:+.3f}; structure effect {d['structure']['mean']:+.3f} [{d['structure']['low']:+.3f}, {d['structure']['high']:+.3f}] (mean stance on a −1…+1 scale).</p>

<h2>3. How to read this</h2>
<p class=note>Section 1 is a descriptive survey finding. It shows association, not cause: vulnerability does not necessarily <em>cause</em> the attitude.
Section 2 is a model output. It is conditional on an assumed crisis mechanism and is not a forecast.</p>
<ul class=small><li>Excluded because stance or income coverage is below 80%: {escape(skipped)}.</li>
<li>Vulnerability is a proxy, not measured crisis exposure. Income steps are self-placed and country-relative.</li>
<li>Survey years differ by country (2017–2022), and some fieldwork fell during COVID-19.</li>
<li>The raw data stays local; only aggregates are published. Source: <code>{escape(source_name)}</code>, doi:10.14281/18241.21.</li></ul>
</main></body></html>"""
