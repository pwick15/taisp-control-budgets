"""Write viz/data/magic-numbers.csv: does each backdoor compare the input against a new number?

A crude regex test for "trigger-shaped" backdoors (if x == 1234): the backdoored program
compares against a number of two or more digits that its honest twin never uses (10, 100 and
1000 excluded). Comments are removed first.

This reads the gitignored Haiku 5.5 eval logs, which only some of us have, so its output is
committed and P09 reads that instead. Rerun it only if the attack set changes:

    uv run python viz/data/derive_magic_numbers.py
"""
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs" / "dataset-haiku55-tm-n500-strip" / "trusted_monitoring"
OUT = Path(__file__).resolve().parent / "magic-numbers.csv"
CMP_NUM = re.compile(r"(==|!=|<=|>=|<|>|%)\s*(\d{2,})")


def code(sample) -> str:
    for m in sample.messages:
        for tc in (getattr(m, "tool_calls", None) or []):
            if tc.function == "submit":
                return "\n".join(line.split("#")[0] for line in tc.arguments["code"].splitlines())
    return ""


def main() -> None:
    att = read_eval_log(glob.glob(str(LOGS / "*attack*.eval"))[0])
    hon = read_eval_log(glob.glob(str(LOGS / "*honest*.eval"))[0])
    honest = {str(s.id): code(s) for s in hon.samples}
    rows = []
    for s in att.samples:
        sid = str(s.id)
        new = ({m.group(2) for m in CMP_NUM.finditer(code(s))}
               - set(re.findall(r"\d{2,}", honest.get(sid, ""))) - {"10", "100", "1000"})
        rows.append((sid, int(bool(new))))
    rows.sort(key=lambda r: int(r[0]) if r[0].isdigit() else r[0])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["sample_id", "magic_number"])
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} backdoors, {sum(r[1] for r in rows)} with a new number")


if __name__ == "__main__":
    main()
