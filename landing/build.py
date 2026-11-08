"""Build web/index.html, the Knights of the Audit landing page, from template.html and data.json.

    python landing/build.py

Cloudflare Pages serves web/ (no build command), so commit web/index.html after rebuilding.
The team's results page is built separately by web/build.py into web/results.html.
"""
import pathlib

here = pathlib.Path(__file__).resolve().parent
body = (here / "template.html").read_text(encoding="utf-8")
data = (here / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
body = body.replace("/*DATA*/", data)
style_end = body.index("</style>") + len("</style>")
page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        + body[:style_end] + "\n</head>\n<body>\n" + body[style_end:] + "\n</body>\n</html>\n")
out = here.parent / "web" / "index.html"
out.write_text(page, encoding="utf-8", newline="\n")
print(f"wrote {out}")
