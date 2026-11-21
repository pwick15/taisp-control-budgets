"""Add the numbers the story page needs on top of the original data.json export.

    python landing/add_story_data.py    # then: python landing/build.py

Writes these keys into landing/data.json and leaves every other key as it was:

- `piles`: how many honest and backdoored programs got each suspicion score (0 to 10), for the
  three knights the cutoff walkthrough uses: Sonnet 5.5 (high), Haiku 5.5 (default) and Ministral
  14B, the jumpy one. Read from the committed per-sample CSVs in results/. The page draws the cutoff
  from these, breaking ties at random, which reproduces the blog post's numbers (shared/cutoff.py).
- `scene`: one honest program and the scores those three knights gave it, to show that every knight
  uses the 0 to 10 scale its own way. Taken from game/data.json, whose scores game/add_cutoffs.py
  checks against results/.
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
sys.path.insert(0, str(HERE.parent))
from shared.cutoff import call, cutoff, scores  # noqa: E402

PILES = {
    "sonnet": "dataset500-sonnet55-um-strip",
    "haiku": "dataset-haiku55-tm-n500-strip",
    "ministral": "dataset500-ministral14b-tm-strip",
}
SCENE_ID = "38"  # "Running track": honest, scored 0, 1 and 10 by the three knights above
GAME = HERE.parent / "game" / "data.json"


def pile(run: str) -> dict:
    """Score (0 to 10) -> count, for honest and backdoored programs."""
    out = {"honest": Counter(), "attack": Counter()}
    with open(RESULTS / f"{run}-samples.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["suspicion"] == "":
                continue
            out["honest" if r["mode"] == "honest" else "attack"][str(round(float(r["suspicion"]) * 10))] += 1
    return {side: dict(sorted(c.items(), key=lambda kv: -float(kv[0]))) for side, c in out.items()}


def scene() -> dict:
    item = next(i for i in json.loads(GAME.read_text(encoding="utf-8"))["items"] if i["id"] == SCENE_ID)
    assert item["mode"] == "honest"
    return {"title": item["title"], "task": item["task"], "code": item["code"],
            "scores": {key: item["scores"][run] for key, run in PILES.items()}}


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
    data["scene"] = scene()
    data.pop("eci", None)
    duel_calls(data)
    DATA.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    for key, p in data["piles"].items():
        print(f"{key}: {sum(p['honest'].values())} honest, {sum(p['attack'].values())} backdoored")
    print(f"wrote {DATA}")


if __name__ == "__main__":
    main()
