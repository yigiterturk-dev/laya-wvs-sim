"""Static HTML report with inline SVG charts (no external requests)."""

from html import escape

GROUP_TITLES = {"age_group": "Age group", "education": "Education", "income": "Household income",
                "employment": "Employment", "vulnerability_band": "Vulnerability proxy"}
GROUP_ORDER = {"income": ["low", "middle", "high"], "education": ["lower", "middle", "upper"],
               "vulnerability_band": ["low", "middle", "high"],
               "employment": ["employed", "retired", "inactive", "unemployed"]}
BLUE, ORANGE, GREY = "#2563eb", "#ea580c", "#9ca3af"


def _fmt(ci, digits=2):
    return f"{ci['mean']:+.{digits}f} <span class=ci>[{ci['low']:+.{digits}f}, {ci['high']:+.{digits}f}]</span>"


def _ordered(field, groups):
    order = GROUP_ORDER.get(field)
    return [g for g in order if g in groups] if order else sorted(groups)


def _sensitivity_svg(sweep):
    width, height, pad = 560, 260, 44
    series = {mode: [(r["strength"], r["delta_changes_per_100"]) for r in rows] for mode, rows in sweep.items()}
    values = [v for rows in series.values() for _, ci in rows for v in (ci["low"], ci["high"])] + [0]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    x = lambda s: pad + (s - 0.2) / 0.8 * (width - 2 * pad)
    y = lambda v: height - pad - (v - lo) / span * (height - 2 * pad)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Sensitivity of change rate to crisis strength">',
             f'<line x1="{pad}" x2="{width - pad}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{GREY}" stroke-dasharray="4 4"/>']
    for tick in (0.2, 0.4, 0.6, 0.8, 1.0):
        parts.append(f'<text x="{x(tick):.1f}" y="{height - pad + 18}" text-anchor="middle">{tick}</text>')
    for value in (lo, 0, hi):
        parts.append(f'<text x="{pad - 6}" y="{y(value) + 4:.1f}" text-anchor="end">{value:+.2f}</text>')
    for mode, color in (("entrenchment", BLUE), ("drift", ORANGE)):
        rows = series[mode]
        band = [(x(s), y(ci["high"])) for s, ci in rows] + [(x(s), y(ci["low"])) for s, ci in reversed(rows)]
        parts.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in band)}" fill="{color}" opacity="0.15"/>')
        parts.append(f'<polyline points="{" ".join(f"{x(s):.1f},{y(ci["mean"]):.1f}" for s, ci in rows)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        last_s, last = rows[-1]
        parts.append(f'<text x="{x(last_s) - 4:.1f}" y="{y(last["mean"]) - 8:.1f}" text-anchor="end" fill="{color}">{mode}</text>')
    parts.append(f'<text x="{width / 2}" y="{height - 6}" text-anchor="middle">crisis strength</text></svg>')
    return "".join(parts)


def _group_bars(real, placebo, field):
    groups = _ordered(field, real)
    values = [v for data in (real, placebo) for g in groups if g in data for v in (data[g]["low"], data[g]["high"])] + [0]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    row, width, left, right = 34, 420, 96, 16
    height = row * len(groups) + 30
    x = lambda v: left + (v - lo) / span * (width - left - right)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(GROUP_TITLES[field])} effect">',
             f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="0" y2="{height - 24}" stroke="{GREY}"/>']
    for i, group in enumerate(groups):
        top = i * row + 4
        parts.append(f'<text x="{left - 8}" y="{top + 16}" text-anchor="end">{escape(group)}</text>')
        for offset, data, color in ((0, real, BLUE), (12, placebo, GREY)):
            if group not in data:
                continue
            ci = data[group]
            a, b = sorted((x(0), x(ci["mean"])))
            parts.append(f'<rect x="{a:.1f}" y="{top + offset}" width="{max(b - a, 1):.1f}" height="10" fill="{color}" rx="2"/>')
            parts.append(f'<line x1="{x(ci["low"]):.1f}" x2="{x(ci["high"]):.1f}" y1="{top + offset + 5}" y2="{top + offset + 5}" stroke="#111827"/>')
    parts.append(f'<text x="{x(lo):.1f}" y="{height - 6}">{lo:+.2f}</text><text x="{x(hi):.1f}" y="{height - 6}" text-anchor="end">{hi:+.2f}</text></svg>')
    return "".join(parts)


def build_html(study, quality, source_name, country):
    design = study["design"]
    head = study["headline"]
    base = study["baseline"]
    missing_rows = "".join(f"<tr><td>{escape(k)}</td><td>{v}</td><td>{v / quality['respondents']:.1%}</td></tr>"
                           for k, v in quality["missing"].items())
    headline_rows = "".join(
        f"<tr><td>{escape(r['scenario'])}</td><td>{r['strength']}</td><td>{_fmt(r['delta_changes_per_100'])}</td>"
        f"<td>{_fmt(r['delta_mean_stance'], 3)}</td></tr>" for r in head.values())
    group_sections = ""
    if "placebo" in study:
        for mode in ("entrenchment", "drift"):
            charts = "".join(
                f"<div class=panel><h3>{GROUP_TITLES[f]}</h3>"
                f"{_group_bars(head[mode]['delta_group_rates'][f], study['placebo'][mode]['delta_group_rates'][f], f)}</div>"
                for f in ("vulnerability_band", "income", "age_group", "education", "employment"))
            group_sections += f"<h3 class=mode>Mode: {mode}</h3><div class=grid>{charts}</div>"
    sensitivity = _sensitivity_svg(study["sensitivity"]) if "sensitivity" in study else ""
    sizes = base["group_sizes"]["vulnerability_band"]
    gov = base["government_share_by_vulnerability"]
    finding = ""
    if "placebo" in study:
        real = head["drift"]["delta_group_rates"]["vulnerability_band"]["high"]
        fake = study["placebo"]["drift"]["delta_group_rates"]["vulnerability_band"]["high"]
        finding = ((f"<p class=note><strong>Data-driven observation.</strong> In the Türkiye sample, {gov.get('high', 0):.1%} of high-vulnerability respondents "
                   f"already say the government should take more responsibility, against {gov.get('low', 0):.1%} in the low band. ")
                   + (f"Under the drift assumption the high band changes less than the placebo predicts: "
                      f"{real['mean']:+.2f} [{real['low']:+.2f}, {real['high']:+.2f}] vs {fake['mean']:+.2f} [{fake['low']:+.2f}, {fake['high']:+.2f}]. "
                      f"The people the crisis assumption targets most have the least room left to move.</p>"
                      if real["high"] < fake["low"] else
                      f"Under the drift assumption the high band changes {real['mean']:+.2f} [{real['low']:+.2f}, {real['high']:+.2f}] "
                      f"vs {fake['mean']:+.2f} [{fake['low']:+.2f}, {fake['high']:+.2f}] in the placebo. The direction fits a ceiling effect "
                      f"(less room left to move), but the intervals overlap, so this run cannot tell them apart.</p>"))
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Laya WVS Türkiye simulation</title><style>
body{{margin:0;background:#fff;color:#111827;font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:32px 20px 64px}}h1{{font-size:28px;margin:0 0 6px}}h2{{margin-top:40px;font-size:20px}}
.lede{{color:#4b5563;max-width:720px}}table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border-bottom:1px solid #e5e7eb;padding:6px 8px;text-align:left}}
.ci{{color:#6b7280;font-size:13px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:16px}}
.panel{{border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px}}.panel h3{{margin:0 0 8px;font-size:15px}}
svg{{width:100%;height:auto;font-size:12px;fill:#374151}}.note{{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px 16px}}
.legend span{{display:inline-block;width:12px;height:12px;border-radius:2px;margin:0 6px -1px 14px}}code{{background:#f3f4f6;padding:1px 5px;border-radius:4px}}
.mode{{margin:24px 0 8px}}.scroll{{overflow-x:auto}}</style></head><body><main>
<h1>What happens to opinion dynamics under an economic-crisis assumption?</h1>
<p class=lede>Agent-based simulation seeded from {quality['respondents']:,} real WVS/EVS respondents in Türkiye (country code {escape(country)}, source <code>{escape(source_name)}</code>).
{design['agents']:,} agents sampled by survey weight, {design['rounds']} rounds, {len(design['seeds'])} paired seeds. The stance is E037: should people or the government take more responsibility?</p>
<p class=note><strong>Read this first.</strong> This is a synthetic experiment. Each crisis mechanism is an assumption. The real survey data decides <em>who</em> the assumption hits and how hard; it does not show that the assumption is true.
Every number below is a model output with a 95% bootstrap CI across seeds.</p>

<h2>1. Headline: scenario minus baseline (paired by seed)</h2>
<p>Baseline: {base['changes_per_100']['mean']:.2f} stance changes per 100 agents per round; mean stance {base['initial_mean_stance']:+.3f} → {base['final_mean_stance']['mean']:+.3f} (−1 people … +1 government).</p>
<div class=scroll><table><tr><th>Scenario</th><th>Strength</th><th>Δ changes / 100 agents / round</th><th>Δ final mean stance</th></tr>{headline_rows}</table></div>
<ul><li><strong>entrenchment</strong>: economically vulnerable agents become less open to persuasion (openness × (1 − strength × vulnerability)).</li>
<li><strong>drift</strong>: vulnerable agents drift toward "government should take responsibility" (per-round chance ∝ strength × vulnerability).</li>
<li><strong>trust_building</strong>: agents who trust the government become more open (openness × (1 + strength × trust)).</li></ul>

<h2>2. Sensitivity: does the direction hold across crisis strengths?</h2>
<p>Δ changes per 100 agents per round versus crisis strength, 10 seeds each, shaded 95% CI.</p><div class=panel>{sensitivity}</div>

<h2>3. Who carries the effect, and is it structure or noise?</h2>
<p>Δ change rate per group (per 100 agents in that group per round). <span class=legend><span style="background:{BLUE}"></span>real respondent profiles<span style="background:{GREY}"></span>placebo: each attribute shuffled independently, so the marginals stay the same and the joint structure is broken</span></p>
<p>If the blue and grey bars differ for a demographic group, the difference comes from how vulnerability actually co-occurs with that group in the Türkiye sample. Vulnerability bands in the sample: {', '.join(f'{k} {v:,}' for k, v in sizes.items())} agents.</p>
{finding}
{group_sections}

<h2>4. Data mapping and quality</h2>
<p>Negative WVS codes (don't know / no answer / not asked) are treated as missing. A missing stance starts in the middle position; a missing attribute is left out of homophily and vulnerability. Vulnerability = mean of (1 − income step), unemployment, and (1 − life satisfaction). It is a proxy, not a measured crisis exposure.</p>
<div class=scroll><table><tr><th>Field</th><th>Missing</th><th>Share</th></tr>{missing_rows}</table></div>

<h2>5. Limits</h2>
<ul><li>Random pairwise mixing; no real network structure.</li><li>Openness and influence are random draws, not measured traits.</li>
<li>One survey wave, so the model is not validated against observed change over time.</li><li>The CIs cover simulation noise across seeds, not survey sampling error.</li><li>Only aggregate outputs are published. The raw CSV stays local and is never embedded.</li></ul>
<p class=ci>Reproduce: <code>python3 run.py --csv EVS_WVS_Joint_Csv_v5_0.csv --country {escape(country)}</code></p>
</main></body></html>"""
