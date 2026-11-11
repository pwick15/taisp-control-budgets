"""Build web/index.html, the Knights of the Audit story page, from template.html and data.json.

    python landing/build.py

Cloudflare Pages serves web/ (no build command), so commit web/index.html after rebuilding.
Shared pieces (fonts, colours, header, footer, character art, outside links) come from shared/
and are inlined, so the built page is one self-contained file. Only the data keys the page uses
are inlined; data.json keeps the rest of the original export. The team's results table is built
separately by web/build.py into web/results.html.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.inline import apply  # noqa: E402

# Keys of data.json the page reads; anything else in the export stays in data.json.
KEEP = ["runs", "piles", "eci", "examples", "caughtBy", "lines", "opus", "nRuns", "nModels", "nRunsCaught", "duel", "boss"]

data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
missing = [k for k in KEEP if k not in data]
if missing:
    sys.exit(f"data.json is missing {missing}: run python landing/add_story_data.py first")
blob = json.dumps({k: data[k] for k in KEEP}, separators=(",", ":")).replace("</", "<\\/")

page = (HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/", blob)
page = apply(page, "story")
out = HERE.parent / "web" / "index.html"
out.write_text(page, encoding="utf-8", newline="\n")
print(f"wrote {out} ({len(page) // 1024} kB)")
