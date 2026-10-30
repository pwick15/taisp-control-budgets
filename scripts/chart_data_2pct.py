"""Write results/analysis/chart-safety-at-2pct.csv (the 2% budget chart in the study summary).

    python3 scripts/analysis_ci.py && python3 scripts/chart_data_2pct.py

Uses the run list and display names from web/build.py so the page and the summary chart stay in step.
"""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("web_build", ROOT / "web" / "build.py")
web_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_build)

LEAD = {"Sonnet 5.5", "Haiku 5.5 · xhigh"}
rows = [r for r in csv.DictReader(open(ROOT / "results" / "analysis" / "safety-with-ci.csv"))
        if float(r["audit_budget_pct"]) == 2.0 and r["run"] in web_build.RUNS]
rows.sort(key=lambda r: -float(r["safety"]))
with open(ROOT / "results" / "analysis" / "chart-safety-at-2pct.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["monitor", "safety", "ci_lo", "ci_hi", "cost_usd_per_sample", "lead"])
    for r in rows:
        name = web_build.RUNS[r["run"]][0]
        w.writerow([name, r["safety"], r["ci_lo"], r["ci_hi"], r["est_cost_usd_per_sample"], int(name in LEAD)])
print(f"wrote {len(rows)} rows")
