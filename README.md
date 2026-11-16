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
- **When it has nothing:** if `outfit` is empty or whitespace it returns the string `"Couldn't write a fit card: there was no outfit suggestion to build it from."` without calling the model. If the model answers with a blank string it returns a plain two-sentence caption built from the listing (item, price, platform) instead of `""` (added in unit 4 as the improvement). If the model can't be reached it raises `generate.ModelUnavailable`, which `run_agent` catches.

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

`python run_eval.py --label before`, caching off, temperature 0.9 → `results/run_2026-11-15_1915_before.md` (41 agent runs, 74 model calls). Criteria 1–2 are written out of 5, so they get 5 tries; criteria 3–5 are written out of 10 ("9 of 10", "10 of 10"), so they get 10. Each try is marked PASS/FAIL by `checks.py::score`, which encodes the "How it's scored" rule written under each criterion in `criteria.md` (committed in `b1829d5`, before this run). `-` = no try 6–10 for a 5-try criterion.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Try 6 | Try 7 | Try 8 | Try 9 | Try 10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | MET (5/5) |
| 2. Impossible query stops before tool 2 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | MET (5/5) |
| 3. Both tools receive `selected_item`'s id | 9 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |
| 4. Fit card: 2–4 sentences, price once, platform once | 9 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |
| 5. Every result ≤ max_price | 10 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |

**Real output from one try**, pasted as text. Produced by `run_eval.py::main` → `agent.py::run_agent` (tools in `tools.py`, search via `mcp_server.py`), scored by `checks.py`:

```
Criterion 1, try 1 (vintage graphic tee under $30) — PASS (3 tools, card)
- selected_item: Vintage Band Tee — Faded Grey ($19.0, depop)
Outfit suggestion:
Outfit one: Vintage Band Tee — Faded Grey paired with Baggy straight-leg jeans, dark wash, Black combat boots, and Black crossbody bag.
Outfit two: Vintage Band Tee — Faded Grey layered under Vintage black denim jacket, paired with Wide-leg khaki trousers and Chunky white sneakers.
Charcoal grey provides a neutral mid-tone anchor that bridges dark denim, earthy khaki, and crisp white accessories effortlessly.
Fit card:
Nothing beats a properly faded band tee that already has that worn-in grunge feel. Snagged this one for just $19 and it's the ultimate neutral anchor for baggy denim or earthy trousers. Listing it over on depop now! #thrifted #bandtee #grunge

Criterion 2, try 1 (designer ballgown size XXS under $5) — PASS (stopped, says what to change)
- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. To get results, try: use broader words for the item — e.g. 'tee', 'jeans', 'jacket', 'dress', 'sneakers' — the search matches words in listing titles and style tags, so brand names and very specific terms often miss; or remove the size and price limits to see what's close.
- selected_item: (none)   search_results: 0   steps: search_listings only

Criterion 3, try 1 (denim jacket under $50) — PASS (lst_007 → both)
- selected_item: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
- tool_inputs: suggest_outfit = lst_007, create_fit_card = lst_007

Criterion 4, try 1 (denim jacket under $50) — PASS (3 sent, price×1, platform×1)
Fit card:
Obsessed with the wash on this cropped Wrangler denim jacket—it gives major effortless streetwear vibes. I'm listing it over on poshmark for $42 so someone else can get good use out of it. Snag it before I change my mind!

#thrifted #denimstyle #poshmarkfinds

Criterion 5, try 1 (graphic tee under $25) — PASS (5 ≤ $25)
- parsed max_price 25.0; 5 search_results, top: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
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
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | 5 PASS ≥ 4. Every try ran search → suggest_outfit → create_fit_card with a non-empty card. |
| 2 | Impossible query stops before suggest_outfit | 5 of 5 | MET (5/5) | 5 PASS = 5. `steps` was only `search_listings` every time, `fit_card` None, message says "To get results, try: …". |
| 3 | Both later tools receive `selected_item`'s id | 9 of 10 | MET (10/10) | 10 PASS ≥ 9, across 10 different items (lst_007, 005, 019, 008, 022, 034, 028, 013, 011, 018). |
| 4 | Fit card 2–4 sentences, price once, platform once | 9 of 10 | MET (10/10) | 10 PASS ≥ 9 under the written rule (`$42`/`$42.00` counts, platform as a whole word). 9 cards had 3 sentences, 1 had 2. |
| 5 | Every result ≤ max_price | 10 of 10 | MET (10/10) | 10 PASS = 10; every returned listing was at or under its ceiling, and no search came back empty. |

**Diagnoses**

There were no misses, so there's no miss to trace to a tool, the branch, the session or the model. Read plainly, that says more about the targets than about the agent:

- **Criteria 2, 3 and 5 test code that has no randomness in it.** The branch, the session hand-off and the price filter are plain Python, so the same input gives the same result every try. Once they worked, they were always going to pass every try. Criterion 3's reason ("occasional AI workflow mistakes") doesn't fit the system: no model touches the id on its way from `session["selected_item"]` to the tools, so 9 of 10 was a target that couldn't really be missed. I'd tighten it to 10 of 10.
- **Criterion 1 also passed every time for a deterministic reason.** The query `vintage graphic tee under $30` always selects the same listing (lst_033, Vintage Band Tee). The only randomness is in the two model calls, and none failed in 10 calls.
- **Criterion 4 is the only one where the model decides the outcome, and it is where the near-misses are.** These runs didn't count against it, but they show where it would break:
  - The empty-wardrobe diagnostic's card wrote the price as **"forty two dollars"**, which my written rule doesn't count. That's a criterion-4 FAIL if it had been scored. The mechanism: the prompt in `tools.py::create_fit_card` says "mention … the price ($42)" but doesn't require that format, so the model sometimes spells it out.
  - Several cards are written **as the seller** ("Listing it over on depop now!", "I'm listing it over on poshmark for $42"), when the user is the buyer. The criterion doesn't check voice, so they pass. The prompt names the platform without saying the user *bought* it there.
- **A gap the criteria never exercised:** `create_fit_card` could return `""` if the model answered blank. That's the reliability gap from last unit's feedback, and with no misses to fix it's what the improvement targets (below).

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — criterion 1, try 1 of the before run (`run_eval.py::run_once` → `agent.py::run_agent`, captured by `trace.py`)

```
[1] parse_query (regex)
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print … +7 more
      →    branch: 10 found → selected lst_033, go to suggest_outfit
[3] suggest_outfit
      in:  dict with keys: new_item, wardrobe
      out: Outfit one: Vintage Band Tee — Faded Grey paired with Baggy straight-leg jeans, dark wash, Black combat boots,…
[4] create_fit_card
      in:  dict with keys: outfit, new_item
      out: Nothing beats a properly faded band tee that already has that worn-in grunge feel. Snagged this one for just $…
```

Four steps against two for the empty search, so the branch is visible. Step 2 is the MCP call. One weakness of my trace: steps 3 and 4 print `dict with keys: …` instead of the item, because I pass `trace.step` a dict and `trace._short` only lists a dict's keys. Which item went in is still recorded in `session["tool_inputs"]` (criterion 3), but the trace alone doesn't show it.

**Empty search**

```
$ python app.py ask 'graphic tee size M under $10' --trace
[1] parse_query (regex)
      in:  graphic tee size M under $10
      out: description='graphic tee', size='M', max_price=10.0
[2] search_listings (via MCP)
      in:  description='graphic tee', size='M', max_price=10.0
      out: [] (empty)
      →    branch: empty → stop, suggest_outfit NOT called

  No listings matched 'graphic tee' in size M under $10. To get results, try: raise your max price to at least $15.

0 model calls this session
```

**On the MCP move:** `search_listings` is registered in `mcp_server.py` (FastMCP, typed inputs `description: str`, `size: str | None`, `max_price: float | None`, description states the empty case). In `agent.py::run_agent` the direct `search_listings(...)` call was replaced by `call_tool("search_listings", {...})` from `mcp_client.py`, wrapped in `try/except MCPError`. Nothing behaved differently: for `('vintage graphic tee', 'M', 30)`, `('designer ballgown', 'XXS', 5)` and `('denim jacket', None, 50)` the MCP result was `==` the direct result (10, 0 and 8 listings, still a `list` of dicts, `[]` stays `[]`). The one visible change is speed — every call starts the server process, so search takes about a second instead of being instant. `_empty_search_message` still calls `search_listings` directly to work out which filter emptied the search; that's for wording the message only.

### Failure modes, triggered on purpose

**1. Empty search** — `python app.py ask 'designer ballgown size XXS under $5'`

```
  No listings matched 'designer ballgown' in size XXS under $5. To get results, try: use broader words for the item — e.g. 'tee', 'jeans', 'jacket', 'dress', 'sneakers' — the search matches words in listing titles and style tags, so brand names and very specific terms often miss; or remove the size and price limits to see what's close.
```

Handler: `agent.py::_empty_search_message`. It re-runs the search with the size removed, then with the price removed, and names whichever one would have returned results (e.g. "raise your max price to at least $15" above).

**2. Empty wardrobe** — `python app.py ask '...' --empty-wardrobe`

Handler: `tools.py::suggest_outfit` checks `wardrobe["items"]`; if empty it asks the model for outfits built from common basics and the answer starts "No wardrobe saved, so here are general ideas:". It never returns `""` (blank model output falls back to a fixed sentence).

**3. Model unavailable** — bad `GEMINI_API_KEY` in `.env`, `python app.py ask 'vintage graphic tee under $30, size M'`

```
  Found a match — Y2K Baby Tee — Butterfly Print ($18.0 on depop) — but couldn't write outfit ideas: the AI model couldn't be reached. Check that GEMINI_API_KEY in .env is correct and that you're online, then run the same query again.
  Details: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

Handler: `agent.py::run_agent` catches `generate.ModelUnavailable` around both model tools and stops with `session["error"]` set; no stack trace.

**Extra: MCP server unreachable** — `mcp_server.py` temporarily renamed

```
  The listing search couldn't run: the search server (mcp_server.py) didn't respond. Run `python mcp_client.py` to see whether it starts, then try the query again.
```


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** one thing, in `tools.py::create_fit_card` (commit `822ce15`). If the model's answer comes back blank, it now returns a plain two-sentence caption built from the listing, e.g. "Thrifted the Vintage Band Tee — Faded Grey for $19 on depop. Styling it with pieces I already own and it just works.", instead of returning `""`. That's the same promise `suggest_outfit` already kept.

**Which failure it was meant to fix:** no criterion missed, so I followed the gap the diagnosis and last unit's feedback named: a blank model answer at the fit-card step. The 41 runs never produced one, so I forced it with `blank_model_check.py`, which replaces `generate` with one that returns `""` for the caption call only (everything else is real) and runs 5 queries, scored with criterion 1's rule.

| `blank_model_check.py` (forced blank caption) | Result |
|---|---|
| Before the change | **0/5**: every run ended with `fit_card=''`, no `error` set, so the user saw an empty "Fit card:" line |
| After the change | **5/5**: every run returned the fallback caption, e.g. `Thrifted the Denim Jacket — Light Wash, Cropped for $42 on poshmark. Styling it with pieces I already own and it just works.` |

### Run Log — After

`python run_eval.py --label after` → `results/run_2026-11-15_1923_after.md` (same scenarios, caching off, 75 model calls; the service rate-limited it 8 times, it waited and retried, and no try failed because of it).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Try 6 | Try 7 | Try 8 | Try 9 | Try 10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | MET (5/5) |
| 2. Impossible query stops before tool 2 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | - | - | - | - | - | MET (5/5) |
| 3. Both tools receive `selected_item`'s id | 9 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |
| 4. Fit card: 2–4 sentences, price once, platform once | 9 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |
| 5. Every result ≤ max_price | 10 of 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | MET (10/10) |

**Did it help, and how do I know:**

On the failure it was aimed at, yes: with a blank model answer, a run now ends with a usable caption 5/5 instead of an empty one 0/5. On the five criteria it changed nothing, and couldn't have: they were already all MET, and the fallback only runs when the model answers blank, which happened 0 times in the 41 after-runs (the fallback text appears in none of the after-run cards). It also didn't break anything: every criterion is still MET with the same counts.

One trade: the fallback caption is generic. It passes criterion 4's rules (2 sentences, price once, platform once) but it isn't the "specific about the vibe" caption the tool is meant to write. That's a better failure than a blank, but it's a fallback, not a fix for whatever made the model answer blank.


---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

No criterion is still missed. That's mostly because the targets were set where they couldn't be missed, so this is what's still weak and what I'd tighten:

- **Criterion 3's target is too low.** 9 of 10 allowed for "AI workflow mistakes", but nothing random sits between `session["selected_item"]` and the tools. I'd make it 10 of 10, across more than 10 queries.
- **Criterion 4 doesn't check the price *format* strictly enough in the prompt, or the voice at all.** The empty-wardrobe card spelled the price out ("forty two dollars"), which my rule counts as a FAIL. Several cards are written as the seller ("Listing it over on depop now!"). Next I'd change the `create_fit_card` prompt to say "write the price exactly as $42" and "I bought this", add a voice check to criterion 4, and score the empty-wardrobe run under criterion 4 too. I stopped there because it's a second prompt change, and this unit allows one improvement.
- **Criterion 1 tests one query.** `vintage graphic tee under $30` always picks the same listing, so 5 tries test the model calls 5 times but the search once. Ten different queries would be a better test.
- **The search ranks loosely.** "vintage" is a tag on most listings, so `vintage graphic tee, size M` ranks a polo shirt and a knit vest above any real tee once the size filter removes the L tees. No criterion checks whether the top result is actually the thing asked for. That's the criterion I'd add: "for 10 queries naming an item type, the selected item's title contains that type in at least 8."
- **The trace shows `dict with keys` for steps 3 and 4** instead of the item id. It's fixable in `agent.py` by passing strings to `trace.step`, but I left it, because the rule for this unit is that the MCP move and one improvement are the only changes.
- **Rate limits are the real-world risk.** The after run hit the 15-requests-a-minute limit 8 times. It recovered every time, but one agent run is 2 model calls, so about 7 runs a minute is the ceiling on the free key.



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
