"""
The runs the test needs. ← UNIT 4, MILESTONE 3

One scenario per criterion in criteria.md. `run_eval.py` runs each one the
number of times in its "tries" (5 for criteria 1-2, which are written out of
5; 10 for criteria 3-5, which are written out of 10) and scores every try with
`checks.py`, using the rules written under each criterion.

A scenario has either "query" (the same query every try) or "queries" (try N
uses queries[N-1]), plus:
    criterion  the number in criteria.md, or None for a diagnostic run
    tries      how many tries
    target     passes needed for MET
"""

TEN_ITEMS = [
    "denim jacket under $50", "corduroy pants", "platform sneakers size 8",
    "chunky knit cardigan", "leather bomber jacket", "reversible bucket hat",
    "suede chelsea boots", "silk slip dress", "cargo pants under $30",
    "linen blazer",
]

SCENARIOS = [
    {
        # Criterion 1: a query the data can match completes all three tools.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
        "tries": 5,
        "target": 4,
    },
    {
        # Criterion 2: the branch. Nothing matches, so it stops before tool 2.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
        "tries": 5,
        "target": 5,
    },
    {
        # Criterion 3: state. Ten runs, each a query whose first match is a
        # different listing.
        "name": "state: 10 matching queries",
        "queries": TEN_ITEMS,
        "wardrobe": "example",
        "criterion": 3,
        "tries": 10,
        "target": 9,
    },
    {
        # Criterion 4: fit cards for 10 different items.
        "name": "fit card: 10 different items",
        "queries": TEN_ITEMS,
        "wardrobe": "example",
        "criterion": 4,
        "tries": 10,
        "target": 9,
    },
    {
        # Criterion 5: the price ceiling, ten different budgets ($15 to $100).
        "name": "price ceiling: 10 budgets",
        "queries": [
            "graphic tee under $25", "denim under $50", "jacket under $75",
            "vintage under $100", "top under $20", "pants under $35",
            "sneakers under $60", "oversized crewneck under $22", "belt under $15",
            "blazer under $40",
        ],
        "wardrobe": "example",
        "criterion": 5,
        "tries": 10,
        "target": 10,
    },
    {
        # Diagnostic, not one of the five: the empty-wardrobe failure mode.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
        "tries": 1,
    },
]

WARDROBES = ("example", "empty")


def query_for(scenario: dict, attempt: int) -> str:
    """The query for try number `attempt` (1-based)."""
    queries = scenario.get("queries")
    if queries:
        return queries[(attempt - 1) % len(queries)]
    return scenario["query"]


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        queries = scenario.get("queries") or [scenario.get("query", "")]
        if not all(q.strip() for q in queries):
            problems.append(f"scenario {i} has an empty query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
