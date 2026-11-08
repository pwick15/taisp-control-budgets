"""Extract per-sample drill-down detail for the auditor's-read backdoors.

    python explorer/extract_detail.py        # -> explorer/detail.json

Reads the inspect_ai `.eval` logs under trajectories/ (big, ~80 MB each, and
gitignored) and writes a small committed `detail.json` that build.py inlines into
the page's bundle. Decoupled from build.py on purpose: the evals are not always
present (2.3 GB, not in git), so the detail is extracted once here and committed,
and build.py degrades gracefully when detail.json is absent.

For each auditor's-read problem (the 51 with gold rings) it captures, once (the
backdoor code and problem are identical across monitor runs, only the monitor's
reasoning differs):
  - the original problem statement
  - the honest solution and the backdoored submission (for a diff) + secret input
  - the outcome: did the backdoor still pass the tests, and did the trigger fire
and, per monitor run that has a trajectory, that monitor's reasoning + suspicion.
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

from inspect_ai.log import read_eval_log

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TRAJ = REPO / "trajectories"
OUT = HERE / "detail.json"

# Canonical run whose evals carry the shared code/problem/outcome (has all 500).
CANON = "dataset-haiku55-tm-n500-strip"
# Featured backdoors to include even without an auditor's read, so every featured
# card (except the honest #184) opens a drawer. 86 and 1305 are already in the 51.
FEATURED_BACKDOORS = [86, 1305, 837]
# Bundle run name -> trajectory dir holding its attack eval (for per-run reasoning).
REASONING_RUNS = {
    "dataset-haiku55-tm-n500-strip": "dataset-haiku55-tm-n500-strip",
    "dataset-qwen38omniflash-none-tm-n500-strip": "dataset-qwen38omniflash-none-tm-n500-strip",
    "dataset-gemini35fl-low-tm-n500-strip": "repair-dataset-gemini35fl-low-tm-n500-strip",
}


def find_eval(dirname: str, mode: str) -> Path | None:
    hits = glob.glob(str(TRAJ / dirname / "**" / f"*-{mode}-*.eval"), recursive=True)
    return Path(sorted(hits)[0]) if hits else None


def ids_with_reads() -> list[int]:
    bundle = json.loads((HERE / "bundle.json").read_text())
    ids = {int(p) for p, m in bundle.get("probs", {}).items() if m.get("quad")}
    ids |= set(FEATURED_BACKDOORS)
    return sorted(ids)


def submit_code(sample) -> tuple[str, str]:
    try:
        sa = json.loads(sample.store["submit_args"])
    except Exception:
        return "", ""
    return sa.get("code", "") or "", sa.get("secret_input", "") or ""


def monitor_reasoning(sample) -> str:
    """The monitor model's critique: the ModelEvent completion carrying <reasoning>."""
    best = ""
    for e in (sample.events or []):
        if type(e).__name__ != "ModelEvent":
            continue
        comp = (e.output.completion if e.output else "") or ""
        if "<reasoning>" in comp or "suspicion" in comp.lower():
            best = comp
    return best.strip()


def outcome(sample) -> dict:
    sc = (sample.scores or {}).get("apps_scorer")
    val = getattr(sc, "value", None) if sc else None
    if not isinstance(val, dict):
        return {}
    def ok(x): return x == "C" or x is True
    return {"passes_tests": ok(val.get("main_task_success")),
            "trigger_fires": ok(val.get("side_task_success"))}


def main() -> None:
    ids = ids_with_reads()
    want = set(ids)
    print(f"auditor's-read problems: {len(ids)}")

    detail: dict[str, dict] = {str(i): {"reasoning": {}} for i in ids}

    # 1. shared code / problem / outcome + honest code, from the canonical run
    atk = find_eval(CANON, "attack")
    hon = find_eval(CANON, "honest")
    if not atk or not hon:
        raise SystemExit(f"canonical evals missing under trajectories/{CANON}/")
    print(f"canonical attack: {atk.name}")
    log = read_eval_log(str(atk))
    for s in (log.samples or []):
        try:
            sid = int(s.id)
        except (TypeError, ValueError):
            continue
        if sid not in want:
            continue
        code, secret = submit_code(s)
        d = detail[str(sid)]
        d["problem"] = (s.metadata or {}).get("main_task_description", "")
        d["backdoor_code"] = code
        d["secret_input"] = secret
        d["outcome"] = outcome(s)
    hlog = read_eval_log(str(hon))
    for s in (hlog.samples or []):
        try:
            sid = int(s.id)
        except (TypeError, ValueError):
            continue
        if sid in want:
            detail[str(sid)]["honest_code"] = submit_code(s)[0]

    # 2. per-run monitor reasoning for the runs that have trajectories
    for run, dirname in REASONING_RUNS.items():
        ev = find_eval(dirname, "attack")
        if not ev:
            print(f"  (no attack eval for {run})")
            continue
        rlog = read_eval_log(str(ev))
        model = rlog.eval.model if rlog.eval else run
        got = 0
        for s in (rlog.samples or []):
            try:
                sid = int(s.id)
            except (TypeError, ValueError):
                continue
            if sid not in want:
                continue
            r = monitor_reasoning(s)
            if r:
                detail[str(sid)]["reasoning"][run] = {"model": model, "text": r}
                got += 1
        print(f"  reasoning {run}: {got}/{len(ids)} (monitor {model})")

    # trim problems that never got code (defensive)
    detail = {k: v for k, v in detail.items() if v.get("backdoor_code")}
    OUT.write_text(json.dumps(detail, separators=(",", ":"), ensure_ascii=False))
    kb = OUT.stat().st_size / 1024
    nreas = sum(len(v["reasoning"]) for v in detail.values())
    print(f"\nwrote {OUT} ({kb:.0f} KB): {len(detail)} problems, {nreas} reasoning transcripts")


if __name__ == "__main__":
    main()
