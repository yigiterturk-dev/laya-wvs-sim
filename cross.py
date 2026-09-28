#!/usr/bin/env python3
"""Cross-national study over every country in the Joint EVS/WVS CSV."""

import argparse
import json
from pathlib import Path

from laya_sim.crossnational import run_crossnational
from laya_sim.crossreport import build_html
from laya_sim.macro import analyse, fetch_worldbank
from laya_sim.wvs import load_all_countries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to EVS_WVS_Joint_Csv_v5_0.csv (kept local)")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--agents", type=int, default=5000)
    parser.add_argument("--out", default="out")
    parser.add_argument("--no-macro", action="store_true", help="Skip the World Bank comparison (no network)")
    args = parser.parse_args()
    years = {}
    result = run_crossnational(load_all_countries(args.csv, years), tuple(range(1, args.seeds + 1)), args.agents,
                               years=years)
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    macro = None
    if not args.no_macro:
        macro = analyse(result["countries"], fetch_worldbank(out / "worldbank.json"))
        (out / "macro.json").write_text(json.dumps(macro, indent=1), encoding="utf-8")
    (out / "crossnational.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    (out / "crossnational.html").write_text(build_html(result, Path(args.csv).name, macro), encoding="utf-8")
    print(f"wrote {out / 'crossnational.json'} and {out / 'crossnational.html'}")


if __name__ == "__main__":
    main()
