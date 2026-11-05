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
    # Sonnet 5.5's effort default IS high: Anthropic documents effort as defaulting to
    # high when omitted, and an explicit-high probe on the real monitor task used 2,319
    # tokens/sample against this run's 2,242, 3.4% apart. Recorded as "high" rather than
    # "default" so the rung is unambiguous later.
    "dataset500-sonnet55-um-strip": ("Sonnet 5.5 · high (default)", "sonnet55", "anthropic", "high"),
    # The v2 pass of this configuration, which is the complete one: the first pass reached
    # only 480/463 of 500 before the API credit ran out and now lives in results/superseded/.
    # "thinking off" is literal here, not a nickname: the low budget produced 0 reasoning
    # tokens on 100% of rows.
    "dataset500-sonnet55-um-effortlow-v2-strip": ("Sonnet 5.5 · low (thinking off)", "sonnet55", "anthropic", "low"),
    "dataset-haiku55-effortxhigh-tm-n500-strip": ("Haiku 5.5 · xhigh", "haiku55", "anthropic", "xhigh"),
    "dataset-haiku55-efforthigh-tm-n500-strip": ("Haiku 5.5 · high", "haiku55", "anthropic", "high"),
    "dataset-haiku55-tm-n500-strip": ("Haiku 5.5 · medium (default)", "haiku55", "anthropic", "medium"),
    "dataset-haiku55-effortlow-tm-n500-strip": ("Haiku 5.5 · low", "haiku55", "anthropic", "low"),
    "dataset-haiku45-tm-n500-strip": ("Haiku 4.5 · no thinking", "haiku45", "anthropic", "off"),
    # GLM-5.3 defaults to max when reasoning_effort is omitted (DeepInfra integration
    # guide, verified on the live endpoint), so this run is the max rung.
    "dataset-glm53-tm-n500-strip": ("GLM-5.3 · max (default)", "glm53", "zhipu", "max"),
    "dataset-glm53-efforthigh-tm-n500-strip": ("GLM-5.3 · high", "glm53", "zhipu", "high"),
    "dataset-glm53-effortlow-tm-n500-strip": ("GLM-5.3 · low", "glm53", "zhipu", "low"),
    "dataset-glm53-effortnone-NOT-AN-ABLATION-tm-n500-strip": ("GLM-5.3 · effort=none (not an ablation)", "glm53", "zhipu", "max"),
    "dataset500-qwen38omniflash-high-tm-strip": ("Qwen 3.8 Omni Flash · high", "qwen38", "alibaba", "high"),
    "dataset500-qwen38omniflash-medium-tm-strip": ("Qwen 3.8 Omni Flash · medium", "qwen38", "alibaba", "medium"),
    "dataset-qwen38omniflash-none-tm-n500-strip": ("Qwen 3.8 Omni Flash · off", "qwen38", "alibaba", "off"),
    "dataset-luna-xhigh-tm-n500-strip": ("GPT-6 Luna · xhigh", "luna", "openai", "xhigh"),
    "dataset-luna-high-tm-n500-strip": ("GPT-6 Luna · high", "luna", "openai", "high"),
    "dataset-gpt6luna-tm-n500-strip": ("GPT-6 Luna · medium (default)", "luna", "openai", "medium"),
    "dataset-luna-low-tm-n500-strip": ("GPT-6 Luna · low", "luna", "openai", "low"),
    "dataset-luna-none-tm-n500-strip": ("GPT-6 Luna · off", "luna", "openai", "off"),
    "dataset-gptoss120b-high-tm-n500-strip": ("gpt-oss-120b · high", "gptoss", "openai", "high"),
    "dataset-gptoss120b-tm-n500-strip": ("gpt-oss-120b · medium (default)", "gptoss", "openai", "medium"),
    "dataset-gptoss120b-low-tm-n500-strip": ("gpt-oss-120b · low", "gptoss", "openai", "low"),
    "dataset500-gemma426b-tm-strip": ("Gemma 4 26B-A4B", "gemma4", "google", "default"),
    # All five of these runs used the SAME model, google/gemini-3.5-flash-lite, verified
    # from the model string recorded in every run. They form ONE reasoning ladder: the
    # first is its off/default rung (flash-lite defaults to thinking off, and it uses the
    # fewest tokens per sample of the five), the rest are explicit effort levels. They were
    # previously split across two display names, one of which ("Gemini 3.5 Flash") names a
    # model that was never run, and that split hid the ladder's monotone decline.
    "dataset500-gemini35lite-tm-strip": ("Gemini 3.5 Flash-Lite · off", "gemini35lite", "google", "off"),
    "dataset-gemini35fl-low-tm-n500-strip": ("Gemini 3.5 Flash-Lite · low", "gemini35lite", "google", "low"),
    "dataset-gemini35fl-medium-tm-n500-strip": ("Gemini 3.5 Flash-Lite · medium", "gemini35lite", "google", "medium"),
    "dataset-gemini35fl-high-tm-n500-strip": ("Gemini 3.5 Flash-Lite · high", "gemini35lite", "google", "high"),
    "dataset-gemini35fl-xhigh-tm-n500-strip": ("Gemini 3.5 Flash-Lite · xhigh", "gemini35lite", "google", "xhigh"),
    "dataset-gemma3-4b-tm-n500-strip": ("Gemma 3 4B", "gemma3", "google", "default"),
    # The 27B counterpart. MODEL-SIZE.md is about this pair, so leaving it off meant the
    # chart could not show the comparison the write-up makes.
    "dataset-gemma3-27b-tm-n500-strip": ("Gemma 3 27B", "gemma3_27b", "google", "default"),
    # Mistral arms. These were unplottable until src/analyze.py carried Mistral prices,
    # since the chart's x axis is cost per sample, so the page silently skipped all three
    # while the results sat in results/.
    "dataset-mistrallarge4-tm-n500-strip": ("Mistral Large 4 · default", "mistrallarge4", "mistral", "default"),
    "dataset500-mistrallarge4-high-tm-strip": ("Mistral Large 4 · high", "mistrallarge4", "mistral", "high"),
    "dataset500-ministral14b-tm-strip": ("Ministral 14B", "ministral14b", "mistral", "default"),
}


MODEL_NAMES = {
    "sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "haiku45": "Haiku 4.5", "luna": "GPT-6 Luna",
    "gptoss": "gpt-oss-120b", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8 Omni Flash",
    "gemini35lite": "Gemini 3.5 Flash-Lite",
    "gemma4": "Gemma 4 26B-A4B", "gemma3": "Gemma 3 4B",
    "gemma3_27b": "Gemma 3 27B",
    "mistrallarge4": "Mistral Large 4", "ministral14b": "Ministral 14B",
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
