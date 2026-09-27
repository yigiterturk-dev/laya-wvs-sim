#!/usr/bin/env python3
"""Run the full study on the Joint EVS/WVS CSV and write JSON + HTML."""

import argparse
import json
from pathlib import Path

from laya_sim.experiment import run_study
from laya_sim.report import build_html
from laya_sim.wvs import data_quality, load_profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to EVS_WVS_Joint_Csv_v5_0.csv (kept local)")
    parser.add_argument("--country", default="792", help="ISO-3166 numeric code; Türkiye = 792")
    parser.add_argument("--agents", type=int, default=10_000)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--out", default="out")
    args = parser.parse_args()

    profiles = load_profiles(args.csv, args.country)
    study = run_study(profiles, tuple(range(1, args.seeds + 1)), args.agents, args.rounds)
    study["data_quality"] = data_quality(profiles)
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    (out / "study.json").write_text(json.dumps(study, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "report.html").write_text(build_html(study, study["data_quality"], Path(args.csv).name, args.country), encoding="utf-8")
    print(f"wrote {out / 'study.json'} and {out / 'report.html'}")


if __name__ == "__main__":
    main()
