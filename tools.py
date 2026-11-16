"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

The full contract for each (inputs with types, return value, empty case) is in
the Tool Inventory section of README.md.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── search helpers ────────────────────────────────────────────────────────────

# Words that say nothing about the item. Without this list, "looking for a tee"
# would score every listing whose description contains "a" or "for".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to", "i",
    "im", "i'm", "me", "my", "want", "need", "looking", "something", "some",
    "find", "show", "any", "please", "that", "is", "it", "under", "below",
    "size", "max", "less", "than", "up", "around", "cheap", "good",
}

# A few phrasings the listings spell differently. Each query word expands to
# these extra words, so "t-shirt" can find a listing titled "Graphic Tee".
_SYNONYMS = {
    "tshirt": {"tee"},
    "t-shirt": {"tee"},
    "sweater": {"crewneck", "knit", "cardigan"},
    "jeans": {"denim"},
    "pants": {"trousers", "jeans"},
    "trousers": {"pants"},
    "shoes": {"sneakers", "boots"},
    "jacket": {"bomber", "windbreaker", "shacket"},
    "hoodie": {"sweatshirt"},
    "sweatshirt": {"crewneck", "hoodie"},
}

# Letter sizes. A "One Size" listing fits any of these.
_LETTER_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}


def _stem(word: str) -> str:
    """Crude plural strip: 'tees' -> 'tee'. Leaves words like 'jeans' alone."""
    if len(word) > 3 and word.endswith("s") and not word.endswith(
        ("ss", "jeans", "pants", "shorts")
    ):
        return word[:-1]
    return word


def _words(text: str) -> list[str]:
    """Lowercase word tokens. Hyphens are kept, so 't-shirt' and 'y2k' survive."""
    return re.findall(r"[a-z0-9][a-z0-9'-]*", (text or "").lower())


def _query_terms(description: str) -> set[str]:
    terms: set[str] = set()
    for word in _words(description):
        if word in _STOPWORDS:
            continue
        word = _stem(word)
        terms.add(word)
        terms |= _SYNONYMS.get(word, set())
    return terms


def _size_tokens(size: str) -> set[str]:
    """
    Turn a size string into the set of sizes it covers.

        "S/M"                   -> {"S", "M"}
        "XL (fits oversized)"   -> {"XL"}
        "One Size / Oversized"  -> every letter size, plus "ONE SIZE"
        "US 8.5"                -> {"8.5", "US 8.5"}
        "W30 L30"               -> {"W30", "30", "L30"}

    Comparing whole tokens, rather than substrings, is what stops "S" from
    matching "US 9" and "L" from matching "XL".
    """
    text = (size or "").upper().strip()
    tokens: set[str] = set()
    if "ONE SIZE" in text:
        tokens |= _LETTER_SIZES | {"ONE SIZE"}
    for match in re.finditer(r"US\s*(\d+(?:\.\d+)?)", text):
        tokens |= {match.group(1), f"US {match.group(1)}"}
    for match in re.finditer(r"\bW(\d+)", text):
        tokens |= {f"W{match.group(1)}", match.group(1)}
    for match in re.finditer(r"\bL(\d+)", text):
        tokens.add(f"L{match.group(1)}")
    for part in re.split(r"[^A-Z0-9.]+", text):
        if part in _LETTER_SIZES:
            tokens.add(part)
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        tokens.add(text)
    return tokens


def _size_matches(wanted: str, listing_size: str) -> bool:
    """True when the size the user asked for is one the listing covers."""
    wanted_tokens = _size_tokens(wanted)
    if not wanted_tokens:
        return False
    if "ONE SIZE" in wanted_tokens:
        return "ONE SIZE" in _size_tokens(listing_size)
    return bool(wanted_tokens & _size_tokens(listing_size))


def _score(listing: dict, terms: set[str]) -> int:
    """Keyword overlap. A title hit counts 3, a tag/color/category hit 2, the
    description or brand 1."""
    title = {_stem(w) for w in _words(listing.get("title", ""))}
    tags = {_stem(listing.get("category", "").lower())}
    for tag in listing.get("style_tags") or []:
        tags |= {_stem(w) for w in _words(tag)}
    colors: set[str] = set()
    for color in listing.get("colors") or []:
        colors |= set(_words(color))
    body = {_stem(w) for w in _words(listing.get("description", ""))}
    body |= set(_words(listing.get("brand") or ""))

    score = 0
    for term in terms:
        if term in title:
            score += 3
        elif term in tags or term in colors:
            score += 2
        elif term in body:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size to filter by, or None to skip size filtering.
                     Matched on whole size tokens, case-insensitively:
                     "M" matches "M", "S/M", "M/L" and any "One Size" listing,
                     but "S" does not match "US 9" and "L" does not match "XL".
                     Shoe sizes ("8", "US 8") and waists ("30", "W30") work too.
        max_price:   maximum price in dollars, inclusive, or None to skip.

    Returns:
        A list of matching listing dicts, best keyword match first (ties go to
        the cheaper item), at most config.SEARCH_RESULT_LIMIT long. Each dict
        is the full listing: id, title, description, category, style_tags,
        size, condition, price (float), colors, brand (str or None), platform.

        Returns an empty list [] when nothing matches — never None, never raises.

    Test it:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    listings = load_listings()

    if max_price is not None:
        listings = [l for l in listings if float(l.get("price", 0)) <= float(max_price)]
    if size:
        listings = [l for l in listings if _size_matches(size, str(l.get("size", "")))]

    terms = _query_terms(description)
    if not terms:
        return []

    scored = [(_score(l, terms), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]
    scored.sort(key=lambda pair: (-pair[0], float(pair[1].get("price", 0))))
    return [l for _, l in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest two outfits.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of
                  wardrobe items (name, category, colors, style_tags, notes).
                  It may be empty.

    Returns:
        A non-empty string: two outfit ideas, naming pieces from the wardrobe.
        With an empty wardrobe, a string that starts "No wardrobe saved, so
        here are general ideas:" and builds the outfits from common basics.
        Never returns "". Raises generate.ModelUnavailable if the model
        can't be reached — the loop handles that.

    Test it:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = (wardrobe or {}).get("items") or []
    item_text = _describe_item(new_item)

    system = (
        "You are a thrift-store stylist. Be concrete and brief. Plain text, no "
        "markdown, no more than 120 words."
    )

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            "You know nothing about their wardrobe. Suggest two outfits built "
            "around this piece using common basics most people own, and name "
            "the basics (e.g. 'straight-leg blue jeans', 'plain white tee'). "
            "Start your answer with exactly: 'No wardrobe saved, so here are "
            "general ideas:'"
        )
    else:
        closet = "\n".join(
            f"- {w.get('name')} ({w.get('category')}; colors: "
            f"{', '.join(w.get('colors') or [])}"
            f"{'; ' + w['notes'] if w.get('notes') else ''})"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            f"Here is what they already own:\n{closet}\n\n"
            "Suggest two outfits that pair the new piece with items from this "
            "list. Name the owned pieces exactly as written above. One line per "
            "outfit, then one sentence on why the colors work."
        )

    text = (generate(prompt, system=system) or "").strip()
    if not text:
        # The model came back blank. Keep the promise of a non-empty string.
        return (
            f"Pair the {new_item.get('title', 'piece')} with simple basics in "
            "neutral colors and let it be the focus of the outfit."
        )
    return text


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A 2-4 sentence caption that mentions the item, its price and its
        platform. If `outfit` is empty or whitespace, returns the message
        "Couldn't write a fit card: there was no outfit suggestion to build it
        from." instead of calling the model. If the model answers with a blank
        string, returns a plain two-sentence caption built from the listing
        instead of "". Raises generate.ModelUnavailable if the model can't be
        reached.

    Test it:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card: there was no outfit suggestion to build "
            "it from."
        )

    price = new_item.get("price")
    price_text = f"${float(price):.0f}" if price is not None else "an unlisted price"
    platform = new_item.get("platform") or "a thrift app"

    system = (
        "You write short, casual social-media captions for thrift finds. Sound "
        "like a real person posting, not an ad. At most three hashtags. Plain text."
    )
    prompt = (
        f"Item:\n{_describe_item(new_item)}\n\n"
        f"How I'm styling it:\n{outfit}\n\n"
        "Write a 2-4 sentence caption for posting this fit. Mention the item, "
        f"the price ({price_text}) and the platform ({platform}) once each, and "
        "say something specific about the vibe."
    )
    text = (generate(prompt, system=system) or "").strip()
    if not text:
        # Unit 4 improvement: the model came back blank. suggest_outfit already
        # promises a non-empty string; this keeps the same promise here, with a
        # plain caption built from the listing (2 sentences, price and platform
        # once each) instead of handing the user "".
        title = new_item.get("title") or "this find"
        return (
            f"Thrifted the {title} for {price_text} on {platform}. "
            "Styling it with pieces I already own and it just works."
        )
    return text


def _describe_item(item: dict) -> str:
    """The listing as prompt text. Leaves out empty fields, like a missing brand."""
    lines = [
        f"title: {item.get('title')}",
        f"category: {item.get('category')}",
        f"price: ${item.get('price')}",
        f"size: {item.get('size')}",
        f"condition: {item.get('condition')}",
        f"colors: {', '.join(item.get('colors') or [])}",
        f"style: {', '.join(item.get('style_tags') or [])}",
        f"platform: {item.get('platform')}",
    ]
    if item.get("brand"):
        lines.append(f"brand: {item['brand']}")
    return "\n".join(lines)
