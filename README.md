# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

You type what you're hunting for in plain language — `vintage graphic tee under $30, size M`. FitFindr pulls the price ceiling and size out of the sentence, searches 40 thrift listings (Depop, thredUp, Poshmark) for the best keyword match that fits both, and picks the top one. It then asks the model for two outfits built from clothes already in your wardrobe and writes a short caption you could post with the fit. If nothing matches, it stops before the outfit step and tells you which filter to loosen and by how much.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size, then ranks what's left by keyword overlap with the description (title hit = 3 points, style tag / color / category hit = 2, description or brand hit = 1) and drops anything scoring 0.
- **Inputs:** `description` (str, keywords like `"vintage graphic tee"`), `size` (str or None — matched on whole size tokens, case-insensitive: `"M"` matches `M`, `S/M`, `M/L` and any `One Size` listing; `"S"` does **not** match `US 9` and `"L"` does **not** match `XL`; shoe sizes `"8"`/`"US 8"` and waists `"30"`/`"W30"` also work; None = no size filter), `max_price` (float or None, dollars, inclusive; None = no ceiling).
- **Returns:** `list[dict]`, best match first (ties → cheaper first), at most `config.SEARCH_RESULT_LIMIT` (10). Each dict is the full listing: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None), `platform` (str).
- **When it has nothing:** an empty list `[]` — never `None`, never an exception. The loop branches on this.

### `suggest_outfit`

- **What it does:** Sends the item and the wardrobe to the model (through `generate()`) and asks for two outfits that use pieces the user already owns, named exactly as they appear in the wardrobe.
- **Inputs:** `new_item` (dict — one listing dict as returned by `search_listings`), `wardrobe` (dict with key `items`: list of dicts with `id`, `name`, `category`, `colors`, `style_tags`, `notes`; the list may be empty).
- **Returns:** a non-empty `str` of at most ~120 words: two outfit lines plus one sentence on why the colors work.
- **When it has nothing:** with an empty wardrobe it still returns a non-empty `str` that starts `"No wardrobe saved, so here are general ideas:"` and builds outfits from common basics. If the model returns a blank string it returns a fixed fallback sentence instead of `""`. If the model can't be reached it raises `generate.ModelUnavailable`, which `run_agent` catches.

### `create_fit_card`

- **What it does:** Sends the item and the outfit text to the model and asks for a casual caption someone would post.
- **Inputs:** `outfit` (str — the text `suggest_outfit` returned), `new_item` (dict — the same listing dict).
- **Returns:** a `str` caption of 2–4 sentences that mentions the item, its price and its platform once each, with at most three hashtags.
- **When it has nothing:** if `outfit` is empty or whitespace it returns the string `"Couldn't write a fit card: there was no outfit suggestion to build it from."` without calling the model. If the model can't be reached it raises `generate.ModelUnavailable`, which `run_agent` catches.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what to change (drop the size, raise the max price to a specific dollar amount, or use broader words) and stop — `suggest_outfit` is never called and `fit_card` stays `None`. Otherwise take the first result as `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

Two smaller stops sit on the same loop: if the parser finds no item words at all it stops before searching, and if the model can't be reached (`ModelUnavailable`) during `suggest_outfit` or `create_fit_card` it stops and says to check the key / connection.

**Where it lives:** `agent.py::run_agent` (the empty-search message is built by `agent.py::_empty_search_message`).

**How the query is parsed:** regex, in `agent.py::parse_query`. A price is pulled from phrases like `under $30`, `below 30`, `up to $30`, `$30 max`; a size from `size M`, `size US 8`, `size 30`. Whatever is left (punctuation stripped) is the description.

**What moves through the session:** `query` → `parsed` (`description`, `size`, `max_price`) → `search_results` → `selected_item` (= `search_results[0]`) → `outfit_suggestion` → `fit_card`. Each step reads its input back out of the session rather than from the previous call's return value. `session["steps"]` records which tools ran, in order, and `session["tool_inputs"]` records the listing `id` that `suggest_outfit` and `create_fit_card` actually received, so it can be compared with `selected_item["id"]`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
