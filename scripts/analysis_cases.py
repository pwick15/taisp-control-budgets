"""What do the hard backdoors have in common? No API calls.

    uv run python scripts/analysis_cases.py [path/to/ds.json]

Joins results/analysis/hard-backdoors.csv (how many of 7 monitors catch each backdoor at a 2% budget)
with the APPS backdoor dataset (offline HF cache) and compares backdoors by source, generating model
and size of the change from the honest solution. Writes results/analysis/case-features.csv.
"""
import csv, difflib, json, os, statistics as st, sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results" / "analysis"


def load_dataset(path=None):
    if path:
        return json.load(open(path))
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    from control_arena import EvalMode
    from control_arena.settings.apps.task.dataset import get_dataset
    out = {}
    for s in get_dataset(has_backdoor_solution=True, mode=EvalMode.ATTACK):
        md = s.metadata["metadata"]
        out[str(s.id)] = {"question": s.input, "solution": md["solutions"][0]["code"], "backdoors": md["backdoors"]}
    return out


def strip_comments(code):
    return "\n".join(l.split("#")[0].rstrip() for l in code.splitlines())


def changed_lines(a, b):
    a, b = strip_comments(a).splitlines(), strip_comments(b).splitlines()
    return sum(1 for l in difflib.ndiff(a, b) if l[:1] in "+-")


ds = load_dataset(sys.argv[1] if len(sys.argv) > 1 else None)
rows = []
for r in csv.DictReader(open(R / "hard-backdoors.csv")):
    d = ds[r["sample_id"]]
    bd = d["backdoors"][0]
    rows.append({
        "sample_id": r["sample_id"], "caught_by": int(r["n_monitors_caught@2%"]),
        "source": bd["source"], "model": bd["model"],
        "changed_lines": changed_lines(d["solution"], bd["backdoor_code"]),
        "code_lines": len(strip_comments(bd["backdoor_code"]).splitlines()),
        "input_chars": len(str(bd["backdoor_input"])),
    })
with open(R / "case-features.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)

def group(key):
    g = defaultdict(list)
    for r in rows: g[r[key]].append(r)
    print(f"\nBy {key}: n, % caught by none, % caught by all 7, median changed lines")
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:32} n={len(v):3}  none={sum(x['caught_by']==0 for x in v)/len(v):5.0%}  all7={sum(x['caught_by']==7 for x in v)/len(v):5.0%}  med_changed={st.median(x['changed_lines'] for x in v)}")

group("source"); group("model")
for name, sel in (("caught by none", lambda x: x["caught_by"] == 0), ("caught by all 7", lambda x: x["caught_by"] == 7)):
    v = [x for x in rows if sel(x)]
    print(f"\n{name}: n={len(v)} median changed lines={st.median(x['changed_lines'] for x in v)}, mean={st.mean(x['changed_lines'] for x in v):.1f}, median code lines={st.median(x['code_lines'] for x in v)}")
# changed-lines buckets
print("\nShare caught by none, by size of change:")
for lo, hi in ((0, 2), (3, 4), (5, 8), (9, 10**6)):
    v = [x for x in rows if lo <= x["changed_lines"] <= hi]
    print(f"  {lo}-{hi if hi<10**6 else '+'} changed lines: n={len(v):3}  none={sum(x['caught_by']==0 for x in v)/max(len(v),1):5.0%}  all7={sum(x['caught_by']==7 for x in v)/max(len(v),1):5.0%}")
