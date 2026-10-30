"""Build web/index.html: one self-contained page (write-up + interactive cost-vs-safety chart).

    uv run python scripts/analysis_ci.py   # refresh results/analysis/safety-with-ci.csv first
    python3 web/build.py

Deploy: point Cloudflare Pages at this repo with build command empty and output directory `web`.
To add a run, add it to RUNS below (the run label is the CSV's `run` column) and rebuild.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CI = HERE.parent / "results" / "analysis" / "safety-with-ci.csv"
BUDGETS = [0.5, 1, 2, 5, 10, 20]

# run label -> (display name, model key, family, reasoning setting)
RUNS = {
    "dataset500-sonnet55-um-strip": ("Sonnet 5.5", "sonnet55", "anthropic", "default"),
    "dataset-haiku55-effortxhigh-tm-n500-strip": ("Haiku 5.5 · xhigh", "haiku55", "anthropic", "xhigh"),
    "dataset-haiku55-efforthigh-tm-n500-strip": ("Haiku 5.5 · high", "haiku55", "anthropic", "high"),
    "dataset-haiku55-tm-n500-strip": ("Haiku 5.5 · medium (default)", "haiku55", "anthropic", "medium"),
    "dataset-haiku55-effortlow-tm-n500-strip": ("Haiku 5.5 · low", "haiku55", "anthropic", "low"),
    "dataset-glm53-tm-n500-strip": ("GLM-5.3 · thinking on", "glm53", "zhipu", "on"),
    "dataset-glm53-thinkoff-tm-n500-strip": ("GLM-5.3 · thinking off", "glm53", "zhipu", "off"),
    "dataset500-qwen38omniflash-high-tm-strip": ("Qwen 3.8 Omni Flash · high", "qwen38", "alibaba", "high"),
    "dataset-luna-xhigh-tm-n500-strip": ("GPT-6 Luna · xhigh", "luna", "openai", "xhigh"),
    "dataset-luna-high-tm-n500-strip": ("GPT-6 Luna · high", "luna", "openai", "high"),
    "dataset-gpt6luna-tm-n500-strip": ("GPT-6 Luna · medium (default)", "luna", "openai", "medium"),
    "dataset-luna-low-tm-n500-strip": ("GPT-6 Luna · low", "luna", "openai", "low"),
    "dataset-luna-none-tm-n500-strip": ("GPT-6 Luna · off", "luna", "openai", "off"),
    "dataset-gptoss120b-high-tm-n500-strip": ("gpt-oss-120b · high", "gptoss", "openai", "high"),
    "dataset-gptoss120b-tm-n500-strip": ("gpt-oss-120b · medium (default)", "gptoss", "openai", "medium"),
    "dataset-gptoss120b-low-tm-n500-strip": ("gpt-oss-120b · low", "gptoss", "openai", "low"),
    "dataset500-gemma426b-tm-strip": ("Gemma 4 26B-A4B", "gemma4", "google", "default"),
    "dataset500-gemini35lite-tm-strip": ("Gemini 3.5 Flash-Lite", "gemini35lite", "google", "default"),
    "dataset-gemini35fl-low-tm-n500-strip": ("Gemini 3.5 Flash · low", "gemini35fl", "google", "low"),
    "dataset-gemini35fl-medium-tm-n500-strip": ("Gemini 3.5 Flash · medium", "gemini35fl", "google", "medium"),
    "dataset-gemini35fl-high-tm-n500-strip": ("Gemini 3.5 Flash · high", "gemini35fl", "google", "high"),
    "dataset-gemini35fl-xhigh-tm-n500-strip": ("Gemini 3.5 Flash · xhigh", "gemini35fl", "google", "xhigh"),
    "dataset-gemma3-4b-tm-n500-strip": ("Gemma 3 4B", "gemma3", "google", "default"),
}


MODEL_NAMES = {
    "sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "luna": "GPT-6 Luna",
    "gptoss": "gpt-oss-120b", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8 Omni Flash",
    "gemini35fl": "Gemini 3.5 Flash", "gemini35lite": "Gemini 3.5 Flash-Lite",
    "gemma4": "Gemma 4 26B-A4B", "gemma3": "Gemma 3 4B",
}


def main() -> None:
    runs: dict[str, dict] = {}
    seen_unknown = set()
    for r in csv.DictReader(open(CI)):
        run = r["run"]
        if run not in RUNS:
            seen_unknown.add(run)
            continue
        b = float(r["audit_budget_pct"])
        if b not in BUDGETS:
            continue
        name, model, family, effort = RUNS[run]
        d = runs.setdefault(run, {
            "name": name, "mname": MODEL_NAMES[model], "model": model, "family": family, "effort": effort,
            "cost": float(r["est_cost_usd_per_sample"]) if r["est_cost_usd_per_sample"] else None, "s": {}})
        d["s"][str(b).rstrip("0").rstrip(".") if b != int(b) else str(int(b))] = [
            float(r["safety"]), float(r["ci_lo"]), float(r["ci_hi"])]
    for run in seen_unknown:
        print(f"skipped (not in RUNS): {run}")
    data = list(runs.values())
    html = (HERE / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*DATA*/[]", json.dumps(data, ensure_ascii=False))
    html = html.replace("{{N}}", str(len(data)))
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {HERE / 'index.html'} with {len(data)} configurations")


if __name__ == "__main__":
    main()
