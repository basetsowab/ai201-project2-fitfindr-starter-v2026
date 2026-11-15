"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one chosen — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "steps": [],                 # names of the tools called, in order
        "tool_inputs": {},           # the item id each model tool actually received
    }


# ── query parsing (regex) ─────────────────────────────────────────────────────

_PRICE_PATTERNS = [
    r"(?:under|below|less than|max(?:imum)?|up to|no more than|<)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$\s*(\d+(?:\.\d+)?)\s*(?:max|or less|and under)?",
]
_SIZE_PATTERN = r"\bsize\s+((?:us\s*)?(?:xxs|xs|xxl|xl|s|m|l|w?\d+(?:\.\d+)?|one size))\b"


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language, with regex.

        "vintage graphic tee under $30, size M"
            -> {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    Anything not found comes back as None. Whatever is left after the price and
    size are removed is the description.
    """
    text = query.strip()
    max_price = None
    size = None

    for pattern in _PRICE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    match = re.search(_SIZE_PATTERN, text, flags=re.IGNORECASE)
    if match:
        size = match.group(1).upper()
        text = text[: match.start()] + " " + text[match.end():]

    description = re.sub(r"[^\w\s'-]", " ", text)
    description = re.sub(r"\s+", " ", description).strip()
    return {"description": description, "size": size, "max_price": max_price}


def _empty_search_message(parsed: dict) -> str:
    """
    Say what the user could change, not just "no results".

    Re-runs the search locally with one filter removed at a time, so the
    message can say which filter emptied it. This is diagnosis for the
    message only — the loop still stops.
    """
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f"'{desc}'"
    if size:
        asked += f" in size {size}"
    if max_price is not None:
        asked += f" under ${max_price:.0f}"

    hints = []
    if size:
        without_size = search_listings(desc, None, max_price)
        if without_size:
            hints.append(
                f"drop the size — {len(without_size)} listing(s) match without it "
                f"(sizes: {', '.join(sorted({l['size'] for l in without_size})[:4])})"
            )
    if max_price is not None:
        without_price = search_listings(desc, size, None)
        if without_price:
            cheapest = min(l["price"] for l in without_price)
            hints.append(f"raise your max price to at least ${cheapest:.0f}")
    if not hints:
        hints.append(
            "use broader words for the item — e.g. 'tee', 'jeans', 'jacket', "
            "'dress', 'sneakers' — the search matches words in listing titles "
            "and style tags, so brand names and very specific terms often miss"
        )
        if size or max_price is not None:
            hints.append("remove the size and price limits to see what's close")

    return (
        f"No listings matched {asked}. To get results, try: "
        + "; or ".join(hints)
        + "."
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Branch rule: if search_listings returns an empty list, put a message in
    session["error"] saying what to change and stop — suggest_outfit is never
    called. Otherwise take the first result as session["selected_item"] and go
    on to suggest_outfit, then create_fit_card.

    Returns the session dict. Check session["error"] first — if it isn't None,
    the run ended early and the later fields are still None.
    """
    session = new_session(query, wardrobe)

    next_step = "parse"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = parse_query(query)
            trace.step("parse_query (regex)", inputs=query, returned=_fmt(session["parsed"]))
            if not session["parsed"]["description"]:
                session["error"] = (
                    "I couldn't tell what item you want. Name the piece, e.g. "
                    "'graphic tee under $30, size M'."
                )
                next_step = "done"
            else:
                next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            results = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            session["search_results"] = results
            session["steps"].append("search_listings")

            # ── THE BRANCH ──
            if not session["search_results"]:
                session["error"] = _empty_search_message(parsed)
                trace.step("search_listings", inputs=_fmt(parsed), returned=results,
                           note="branch: empty → stop, suggest_outfit NOT called")
                next_step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                trace.step("search_listings", inputs=_fmt(parsed), returned=results,
                           note=f"branch: {len(results)} found → selected "
                                f"{session['selected_item']['id']}, go to suggest_outfit")
                next_step = "outfit"

        elif next_step == "outfit":
            item = session["selected_item"]          # read back out of the session
            session["tool_inputs"]["suggest_outfit"] = item.get("id")
            try:
                session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            except ModelUnavailable as exc:
                session["error"] = _model_down_message("outfit ideas", item, exc)
                trace.step("suggest_outfit", inputs={"new_item": item},
                           returned="ModelUnavailable", note="stop: model unreachable")
                next_step = "done"
                continue
            session["steps"].append("suggest_outfit")
            n_items = len((session["wardrobe"] or {}).get("items") or [])
            trace.step("suggest_outfit",
                       inputs={"new_item": f"{item['id']} {item['title']}",
                               "wardrobe": f"{n_items} items"},
                       returned=session["outfit_suggestion"])
            next_step = "card"

        elif next_step == "card":
            item = session["selected_item"]
            outfit = session["outfit_suggestion"]
            session["tool_inputs"]["create_fit_card"] = item.get("id")
            try:
                session["fit_card"] = create_fit_card(outfit, item)
            except ModelUnavailable as exc:
                session["error"] = _model_down_message("the fit card", item, exc)
                trace.step("create_fit_card", inputs={"new_item": item},
                           returned="ModelUnavailable", note="stop: model unreachable")
                next_step = "done"
                continue
            session["steps"].append("create_fit_card")
            trace.step("create_fit_card",
                       inputs={"outfit": outfit, "new_item": f"{item['id']} {item['title']}"},
                       returned=session["fit_card"])
            next_step = "done"

    return session


def _fmt(parsed: dict) -> str:
    """Parsed query as one readable line for the trace."""
    return ", ".join(f"{k}={v!r}" for k, v in parsed.items())


def _model_down_message(what: str, item: dict, exc: Exception) -> str:
    return (
        f"Found a match — {item.get('title')} (${item.get('price')} on "
        f"{item.get('platform')}) — but couldn't write {what}: the AI model "
        f"couldn't be reached. Check that GEMINI_API_KEY in .env is correct and "
        f"that you're online, then run the same query again.\n  Details: {exc}"
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))
