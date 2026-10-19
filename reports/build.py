"""Build the results viewer: one HTML page per experiment, plus an index.

    uv run python reports/build.py            # build every experiment in reports/experiments/
    uv run python reports/build.py --open     # ...then open the index in your browser
    uv run python reports/build.py --template # also build the example in _template.py

Pages are written to reports/site/ (gitignored). Each page is one self-contained HTML file, so
you can email or upload it on its own. To add an experiment, copy
reports/experiments/_template.py to reports/experiments/<your-slug>.py and fill it in.
"""
import importlib.util
import sys
import traceback
import webbrowser
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPORTS_DIR))

from viewer.components import render_index, render_report  # noqa: E402

SITE_DIR = REPORTS_DIR / "site"


def load_report(path: Path):
    spec = importlib.util.spec_from_file_location(f"report_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.build()
    report.slug = path.stem.lstrip("_")
    return report


def main() -> int:
    include_template = "--template" in sys.argv
    paths = sorted(p for p in (REPORTS_DIR / "experiments").glob("*.py")
                   if not p.name.startswith("_") or (include_template and p.name == "_template.py"))
    SITE_DIR.mkdir(exist_ok=True)
    reports, failed = [], []
    for path in paths:
        try:
            report = load_report(path)
        except Exception:
            failed.append(path.name)
            print(f"FAILED {path.name}\n{traceback.format_exc()}")
            continue
        (SITE_DIR / f"{report.slug}.html").write_text(render_report(report))
        reports.append(report)
        print(f"built   {SITE_DIR / (report.slug + '.html')}")
    (SITE_DIR / "index.html").write_text(render_index(reports))
    print(f"index   {SITE_DIR / 'index.html'}")
    if "--open" in sys.argv:
        webbrowser.open((SITE_DIR / "index.html").as_uri())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
