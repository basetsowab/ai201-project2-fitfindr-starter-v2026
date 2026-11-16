"""
The scoring rules from criteria.md, as code. ← UNIT 4, MILESTONE 3

Each function takes the finished session from one try (or None if the run
crashed) and returns (passed, short_reason). The rules are the "How it's
scored" notes under each criterion in criteria.md, written before any run —
if this file and criteria.md ever disagree, criteria.md is the standard.

run_eval.py calls score() for every try and fills in the PASS/FAIL cells.
"""

import re

THREE_TOOLS = ["search_listings", "suggest_outfit", "create_fit_card"]


def c1_completes(s):
    if s is None:
        return False, "crashed"
    if s.get("error"):
        return False, "stopped: " + str(s["error"])[:50]
    if s.get("steps") != THREE_TOOLS:
        return False, f"steps={s.get('steps')}"
    if not (s.get("fit_card") or "").strip():
        return False, "fit_card empty"
    return True, "3 tools, card"


def c2_stops(s):
    if s is None:
        return False, "crashed"
    if s.get("steps") != ["search_listings"]:
        return False, f"steps={s.get('steps')}"
    if s.get("fit_card") is not None:
        return False, "fit_card set"
    err = s.get("error") or ""
    m = re.search(r"To get results, try:\s*(\S.*)", err)
    if not m:
        return False, "message names nothing to change"
    return True, "stopped, says what to change"


def c3_same_item(s):
    if s is None:
        return False, "crashed"
    if s.get("error"):
        return False, "stopped early: " + str(s["error"])[:40]
    sel = (s.get("selected_item") or {}).get("id")
    got = s.get("tool_inputs") or {}
    a, b = got.get("suggest_outfit"), got.get("create_fit_card")
    if sel and a == sel and b == sel:
        return True, f"{sel} → both"
    return False, f"selected={sel} outfit={a} card={b}"


def _sentences(card: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", card.strip())
    real = []
    for p in pieces:
        # Drop hashtags and anything that isn't a letter or digit; what's left
        # has to contain a word for the piece to count as a sentence.
        stripped = re.sub(r"#\w+", "", p)
        if re.search(r"[A-Za-z0-9]", stripped):
            real.append(p)
    return real


def _price_count(card: str, price: float) -> int:
    dollars = int(round(float(price)))
    return len(re.findall(rf"\${dollars}(?:\.00)?(?![\d.]*\d)", card))


def _platform_count(card: str, platform: str) -> int:
    return len(re.findall(rf"(?<![#\w]){re.escape(platform)}(?!\w)", card, flags=re.IGNORECASE))


def c4_fit_card(s):
    if s is None:
        return False, "crashed"
    card = (s.get("fit_card") or "").strip()
    item = s.get("selected_item") or {}
    if not card or not item:
        return False, "no fit card" + (": " + str(s.get("error"))[:40] if s.get("error") else "")
    n = len(_sentences(card))
    p = _price_count(card, item.get("price", 0))
    pl = _platform_count(card, item.get("platform", ""))
    ok = 2 <= n <= 4 and p == 1 and pl == 1
    return ok, f"{n} sent, price×{p}, platform×{pl}"


def c5_price_ceiling(s):
    if s is None:
        return False, "crashed"
    ceiling = (s.get("parsed") or {}).get("max_price")
    results = s.get("search_results") or []
    if ceiling is None:
        return False, "no max_price parsed"
    if not results:
        return False, "no results to check"
    over = [r for r in results
            if not isinstance(r.get("price"), (int, float)) or r["price"] > ceiling]
    if over:
        return False, f"{len(over)} over ${ceiling:.0f}"
    return True, f"{len(results)} ≤ ${ceiling:.0f}"


CHECKS = {1: c1_completes, 2: c2_stops, 3: c3_same_item, 4: c4_fit_card, 5: c5_price_ceiling}


def score(criterion, session):
    fn = CHECKS.get(criterion)
    if fn is None:
        return None, ""
    return fn(session)
