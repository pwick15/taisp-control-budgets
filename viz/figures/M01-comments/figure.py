"""M01: snapshot of Marnick's view 'cases-catch-set-upset'. No generator yet: see viz/HANDOVER.md."""

META = {
    "id": "M01",
    "kind": "snapshot",
    "title": "Half the stored backdoors confess in a comment",
    "section": "results",
    "order": 120,
    "caption": "Three ways to flag a backdoor: a six-word regex for comments that admit to a bug, a monitor reading the code with comments deleted, and the same monitor with comments left in. Each bar counts programs caught by exactly that combination.",
    "notes": [
        "These are Marnick's numbers. Confirm the 51.8% regex figure and the +9.2 / +12.2 point gaps with him before quoting.",
        "Four papers strip comments for this reason and none measures what it does to a monitor ranking. Re-scoring the top monitors with comments kept is a cheap side result (Marnick priced it at about $18)."
    ],
    "height": 440,
    "source": "Marnick's data explorer (marnick-data-2, built 2026-11-02), view 'cases-catch-set-upset'. Copied as exported; its generator isn't in the repo yet.",
}
