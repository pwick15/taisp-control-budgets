"""P11: for each model that wrote backdoors, how many of them got past our seven monitors."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P11",
    "title": "Who wrote the backdoor matters more than which monitor reads it",
    "section": "results",
    "order": 110,
    "caption": ("Each bar is every backdoor one model wrote, split by how many of our seven monitors caught "
                "it at a 2% budget. On the right is the 95% range for the share missed by all seven."),
    "notes": [
        "Most groups are small and their ranges overlap. Only the gap between o3-mini and o1-mini is clearly "
        "real, so say this with the caveat that more backdoors per model are needed.",
        "Models didn't write backdoors for the same problems, so problem difficulty is mixed in with the "
        "writer's skill. A fair test would have every model attack the same problems.",
        "o3-mini's backdoors differ most from the reference solution (median lines changed is in the CSV), so "
        "they may be conspicuous rewrites.",
        "For the recommendations: report catch rates per attack source, not just the average.",
    ],
}

PARTS = [("Missed by all 7", "@s7", "@on-strong"), ("Missed by some", "@warning/0.6", "@on-bright"),
         ("Caught by all 7", "@context", "@on-pale")]
NAMES = {
    "unknown": "Original APPS", "openai/o1-mini": "o1-mini", "openai/o3-mini": "o3-mini",
    "openai/gpt-4o-mini": "GPT-4o mini", "openai/gpt-4o": "GPT-4o", "openai/gpt-3.5-turbo": "GPT-3.5 Turbo",
    "anthropic/claude-3-5-haiku-latest": "Claude 3.5 Haiku", "anthropic/claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
    "anthropic/claude-3-7-sonnet-thinking-latest": "Claude 3.7 Sonnet thinking",
    "google/gemini-2.0-flash": "Gemini 2.0 Flash",
}


def build() -> Figure:
    cf = S.cases()
    g = cf.groupby("model").agg(n=("caught_by", "size"), missed_all=("caught_by", lambda s: int((s == 0).sum())),
                                missed_some=("caught_by", lambda s: int(((s > 0) & (s < 7)).sum())),
                                caught_all=("caught_by", lambda s: int((s == 7).sum())),
                                median_lines=("changed_lines", "median")).reset_index()
    g["missed_all_share"] = g.missed_all / g.n
    g = g.sort_values(["missed_all_share", "n"], ascending=[False, False]).reset_index(drop=True)
    g["writer"] = [NAMES.get(m, m.split("/")[-1].replace("-latest", "")) for m in g.model]
    rows = [(r.writer, int(r.n), [r.missed_all, r.missed_some, r.caught_all]) for r in g.itertuples()]
    option = C.partition_bars(rows, PARTS, "Share of that model's backdoors", "Missed by all, 95% range")
    return Figure(option=option, height=110 + 40 * len(rows),
                  data=g[["writer", "model", "n", "missed_all", "missed_some", "caught_all", "median_lines"]])
