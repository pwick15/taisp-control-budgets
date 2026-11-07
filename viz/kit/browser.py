"""Open the built gallery in a headless browser and run its layout checks (python -m viz check)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import core

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
]


def find_browser() -> str | None:
    """A Chromium-based browser already on this machine, so Playwright needn't download one.
    Set VIZ_BROWSER to a browser executable to override."""
    cands = [os.environ.get("VIZ_BROWSER")] + CANDIDATES
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"):
        cands.append(shutil.which(name))
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


def run(ids: list[str] | None) -> tuple[list[dict], list[str], dict, dict]:
    """Returns (per-figure results from the page, page errors, {(id, theme): png bytes} for html figures,
    {id: GIF export result or {"error": ...}} for figures with a dial)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright isn't installed. Run `uv sync` from the repo root (it's in the dev group).") from None
    with sync_playwright() as p:
        exe = find_browser()
        try:
            browser = p.chromium.launch(executable_path=exe, headless=True) if exe else p.chromium.launch(headless=True)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"couldn't start a browser ({e}). Install Chrome, set VIZ_BROWSER, "
                               "or run `uv run playwright install chromium`.") from None
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(core.GALLERY.as_uri())
            page.wait_for_function("window.__viz && window.__viz.ready === true", timeout=60_000)
            results = page.evaluate("ids => window.__viz.checkAll(ids)", ids or [])
            gifs: dict = {}
            for fid in dict.fromkeys(r["id"] for r in results if not r.get("html") and r.get("step", 0) > 0):
                try:
                    gifs[fid] = page.evaluate("id => window.__viz.checkGif(id, false)", fid)
                except Exception as e:  # noqa: BLE001
                    gifs[fid] = {"error": str(e).splitlines()[0][:200]}
            shots: dict = {}
            html_ids = [r["id"] for r in results if r.get("html")]
            for theme in ("light", "dark"):
                if not html_ids:
                    break
                page.evaluate("t => window.__viz.setTheme(t)", theme)
                for fid in html_ids:
                    box = page.locator(f"article#{fid} .chart")
                    box.scroll_into_view_if_needed()
                    page.wait_for_timeout(1200)
                    shots[(fid, theme)] = box.screenshot()
        finally:
            browser.close()
    return results, errors, shots, gifs
