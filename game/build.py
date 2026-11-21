"""Build web/spot-the-backdoor.html, the Spot the Backdoor game, from template.html and data.json.

    python game/build.py

Cloudflare Pages serves web/ (no build command), so commit web/spot-the-backdoor.html after rebuilding.
It is served at /spot-the-backdoor, the address the game has had since PR #47.
Shared pieces (fonts, colours, header, footer, character art, the walkthrough) come from shared/
and are inlined, so the built page is one self-contained file.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.inline import apply  # noqa: E402

data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = apply((HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/", blob), "game")
out = HERE.parent / "web" / "spot-the-backdoor.html"
out.write_text(page, encoding="utf-8", newline="\n")
print(f"wrote {out} ({len(page) // 1024} kB, {len(data['items'])} programs)")
