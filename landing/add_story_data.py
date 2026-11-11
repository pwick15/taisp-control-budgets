"""Add the numbers the story page needs on top of the original data.json export.

    python landing/add_story_data.py    # then: python landing/build.py

Writes these keys into landing/data.json and leaves every other key as it was:

- `piles`: how many honest and backdoored programs got each suspicion score, for the two knights
  the page walks through (Sonnet 5.5 at high, Haiku 5.5 at xhigh). Read from the committed
  per-sample CSVs in results/. The page turns these into the squares and the audit-budget line,
  breaking ties at random, which reproduces the blog post's numbers (shared/cutoff.py).
- `eci`: each model's score on Epoch AI's Capabilities Index, for the "can you trust your knight"
  figure (source: https://epoch.ai/data/eci_scores.csv, CC BY, read 2026-11-09). Read from
  viz/data/eci-scores.csv when that file is on this branch, otherwise from the copy below (taken
  from the figures/setup-and-results-updates branch). Epoch has not scored Qwen 3.8 Omni Flash,
  Gemma 3 4B or Ministral 14B, so they are left out.
- `duel.calls`: every knight's call on every program in the duel, using the study's 2% rule from
  shared/cutoff.py ("2" always checked, "1" tied at the cutoff and checked with chance `p`, "0"
  not checked), in the order of `duel.aid` and `duel.hid`. It replaces the original export's
  `duel.runs`, which skipped tied programs. Each program in the duel pool also gets `n`, how many
  setups always check it, and `t`, how many tie at their cutoff.
"""
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
DATA = HERE / "data.json"
ECI_CSV = HERE.parent / "viz" / "data" / "eci-scores.csv"
sys.path.insert(0, str(HERE.parent))
from shared.cutoff import call, cutoff, scores  # noqa: E402

PILES = {
    "sonnet": "dataset500-sonnet55-um-strip",
    "haikuX": "dataset-haiku55-effortxhigh-tm-n500-strip",
}

# (name, ECI score, role). Writers made the 500 backdoors; monitors scored them.
ECI = [
    ("GPT-3.5 Turbo", 113.26, "writer"), ("GPT-4o mini", 124.05, "writer"), ("Claude 3.5 Haiku", 125.02, "writer"),
    ("GPT-4o", 127.05, "writer"), ("Gemini 2.0 Flash", 134.03, "writer"), ("o1-mini", 135.39, "writer"),
    ("o3-mini", 140.64, "writer"), ("Claude 3.7 Sonnet", 140.99, "writer"),
    ("Gemma 3 27B", 127.66, "knight"), ("gpt-oss-120b", 140.22, "knight"), ("Gemma 4 26B", 141.69, "knight"),
    ("Haiku 4.5", 142.82, "knight"), ("Gemini 3.5 Flash-Lite", 145.59, "knight"), ("Mistral Large 4", 154.66, "knight"),
    ("GPT-6 Luna", 156.68, "knight"), ("GLM-5.3", 156.91, "knight"), ("Haiku 5.5", 160.22, "knight"),
    ("Sonnet 5.5", 166.24, "knight"),
]


def pile(run: str) -> dict:
    """Score -> count, for honest and backdoored programs. Scores are on 0 to 1 (score / 10)."""
    out = {"honest": Counter(), "attack": Counter()}
    with open(RESULTS / f"{run}-samples.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["suspicion"] == "":
                continue
            out["honest" if r["mode"] == "honest" else "attack"][str(round(float(r["suspicion"]), 2))] += 1
    return {side: dict(sorted(c.items(), key=lambda kv: -float(kv[0]))) for side, c in out.items()}


def eci() -> list[dict]:
    if not ECI_CSV.exists():
        return [{"name": n, "eci": v, "role": role} for n, v, role in ECI]
    names = {n: n for n, _, _ in ECI}
    short = {"Claude Opus 5.5": None, "Claude Sonnet 5.5": "Sonnet 5.5", "Claude Haiku 5.5": "Haiku 5.5",
             "Claude Haiku 4.5": "Haiku 4.5", "Gemma 4 26B A4B": "Gemma 4 26B", "GPT-4o (Aug 2024)": "GPT-4o",
             "Gemini 2.0 Flash (Feb 2025)": "Gemini 2.0 Flash", "GPT-3.5 Turbo (Jan 2024)": "GPT-3.5 Turbo"}
    out, seen = [], set()
    with open(ECI_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if not r["eci"]:
                continue
            name = short.get(r["eci_name"], names.get(r["eci_name"], r["eci_name"]))
            role = "writer" if r["role"] == "writer" else "knight"
            if name is None or (name, role) in seen:
                continue
            seen.add((name, role))
            out.append({"name": name, "eci": float(r["eci"]), "role": role})
    return out


def duel_calls(data: dict) -> None:
    """Every knight's call on every duel program under the study's 2% rule."""
    spec = importlib.util.spec_from_file_location("web_build", HERE.parent / "web" / "build.py")
    web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web)
    run_of = {label[0]: run for run, label in web.RUNS.items()}
    du = data["duel"]
    calls = {}
    for name in du.get("runs", du.get("calls", {})):
        sc = scores(run_of[name])
        cut, p = cutoff(list(sc["honest"].values()), 2.0)
        calls[name] = {"a": "".join(call(sc["attack"].get(i), cut, p) for i in du["aid"]),
                       "h": "".join(call(sc["honest"].get(i), cut, p) for i in du["hid"]),
                       "p": round(p, 4)}
    du["calls"] = calls
    du.pop("runs", None)
    for side, ids in (("a", du["aid"]), ("h", du["hid"])):
        pos = {x: k for k, x in enumerate(ids)}
        for item in du["pool"][side]:
            k = pos[item["i"]]
            item["n"] = sum(c[side][k] == "2" for c in calls.values())
            item["t"] = sum(c[side][k] == "1" for c in calls.values())


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    data["piles"] = {key: pile(run) for key, run in PILES.items()}
    data["eci"] = eci()
    duel_calls(data)
    DATA.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    for key, p in data["piles"].items():
        print(f"{key}: {sum(p['honest'].values())} honest, {sum(p['attack'].values())} backdoored")
    print(f"wrote {DATA}")


if __name__ == "__main__":
    main()
