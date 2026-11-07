"""P15: the same histograms as P14 with the monitors asked for a 0 to 100 score."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P15",
    "title": "On a 0 to 100 scale, honest scores spread out",
    "section": "appendix",
    "order": 30,
    "caption": ("The same layout as P14 for the same monitors and programs, prompted for a 0 to 100 score and drawn "
                "on the same 0 to 1 axis. Sonnet uses {distinct0} distinct honest scores and Haiku xhigh "
                "{distinct1}; their most common score holds {top0:.0f}% and {top1:.0f}% of honest programs."),
    "notes": [],
    "height": 430,
}


def build() -> Figure:
    option, rows, facts = C.score_histograms([(S.SONNET_100, "Sonnet 5.5"), (S.HAIKU_X_100, "Haiku 5.5 · xhigh")],
                                             0.01, "0 to 100")
    return Figure(option=option, data=rows, facts=facts)
