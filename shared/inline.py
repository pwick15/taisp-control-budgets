"""Inline the site's shared pieces into a page, so every built page stays one self-contained file.

Each page's build script calls `apply(html, page)`, where `page` is "story", "game" or "data". It
replaces these markers in the page template:

    <!--SITE:HEAD-->     fonts, the theme bootstrap and shared/site.css (put it inside <head>)
    <!--SITE:ART-->      the character art (knight, ninja, auditor, scrolls) as SVG symbols
    <!--SITE:HEADER-->   the site header and nav, with this page marked as current
    <!--SITE:FOOTER-->   the site footer
    /*SITE:JS*/          shared/site.js (the theme switch)
    /*SITE:TOUR*/        shared/tour.js (the walkthrough overlay)
    {{BLOG}} {{REPO}}    the outside links below

The links live here so every page points at the same place.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINKS = {
    "BLOG": "https://substack.com/home/post/p-223980168",
    "REPO": "https://github.com/pwick15/taisp-control-budgets",
}
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:ital,wght@0,500;0,600;0,700;1,600&'
    'family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">\n'
)
# Runs before first paint, so a stored light/dark choice never flashes the other theme.
BOOT = ('<script>(function(){try{var t=localStorage.getItem("kota-theme");'
        'if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}catch(e){}})();</script>\n')


def read(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def apply(html: str, page: str) -> str:
    header = read("header.html").replace(f'data-page="{page}"', f'data-page="{page}" aria-current="page"')
    parts = {
        "<!--SITE:HEAD-->": FONTS + BOOT + "<style>\n" + read("site.css") + "</style>",
        "<!--SITE:ART-->": read("art.svg").strip(),
        "<!--SITE:HEADER-->": header.strip(),
        "<!--SITE:FOOTER-->": read("footer.html").strip(),
        "/*SITE:JS*/": read("site.js"),
        "/*SITE:TOUR*/": read("tour.js"),
    }
    for marker, text in parts.items():
        html = html.replace(marker, text)
    for key, url in LINKS.items():
        html = html.replace("{{" + key + "}}", url)
    return html
