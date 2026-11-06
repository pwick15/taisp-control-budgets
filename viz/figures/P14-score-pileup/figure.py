"""P14: how often Sonnet and Haiku xhigh give each 0 to 10 suspicion score, honest vs backdoored."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P14",
    "title": "On a 0 to 10 scale, honest programs pile up on one score",
    "section": "appendix",
    "order": 20,
    "caption": ("Programs per suspicion score, honest in grey and backdoored in red, on a log scale so small counts "
                "show. The shaded region is what a requested 2% budget audits when only scores above the cutoff count. "
                "Sonnet gives {top0:.0f}% of honest programs one score; Haiku xhigh {top1:.0f}%."),
    "notes": [
        "Random tie-breaking fixes fairness, not sample size. At 500 honest programs a 1% budget still rests on 5 of "
        "them. The other fixes are a 0 to 100 scale (P15, P08) and more honest programs.",
    ],
    "height": 430,
}


def build() -> Figure:
    option, rows, facts = C.score_histograms([(S.SONNET, "Sonnet 5.5"), (S.HAIKU_X, "Haiku 5.5 · xhigh")], 0.1, "0 to 10")
    return Figure(option=option, data=rows, facts=facts)
