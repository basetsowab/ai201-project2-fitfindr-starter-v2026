# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->

---

## Criterion 3: State Management and Item Consistency

**Success criterion:** In at least 9 out of 10 test runs, both `suggest_outfit` and `create_fit_card` should receive the same item ID as `session["selected_item"]["id"]`.

**Why:** One of the most important parts of FitFindr is making sure the application remembers which clothing item the user selected. If someone chooses a particular shirt, jacket, or pair of shoes, the AI should continue using that item throughout the outfit recommendation process.

I would check the item IDs recorded in `session["tool_inputs"]` after each run and compare them with the ID stored in `session["selected_item"]`. A test only passes if both tools receive the correct selected item ID.

I chose 9 out of 10 as an initial testing target because occasional AI workflow mistakes may happen, but I still expect the application to maintain consistent state. Ideally, this should eventually reach 10 out of 10 because recommending an outfit for the wrong item would make the application unreliable.

---

## Criterion 4: Fit Card Quality and Formatting

**Success criterion:** In at least 9 out of 10 generated fit cards, the description should contain 2–4 sentences, with the selected item's price appearing exactly once and its platform appearing exactly once.

**Why:** The fit card is one of the main features users interact with, so I want the information to be clear, readable, and consistent.

If the description is too long, users might lose interest or have difficulty understanding the recommendation. If it is too short, it might not provide enough information about the outfit.

I also think including the price and platform is important because users need to know how much the clothing item costs and where they can find it.

For testing, I would generate 10 fit cards using different clothing items and count how many meet all three requirements. A card would fail if its description had fewer than 2 or more than 4 sentences, omitted the price or platform, or repeated either detail.

Although the language model might not always follow formatting instructions perfectly, I want the application to produce consistent results.

---

## Criterion 5: Price Filter Accuracy

**Success criterion:** In 10 out of 10 test searches that specify a `max_price`, every returned clothing item should have a price less than or equal to the user's selected maximum.

**Why:** One of the reasons someone might use FitFindr is to find clothing that fits their budget. If the user sets a maximum price of $50, the application should not recommend clothing that costs $70 or $100.

For testing, I would run 10 searches using different maximum prices, such as $25, $50, $75, and $100. I would then inspect the returned results to make sure none exceed the specified budget.

A test would only pass if every returned item has a valid price that is within the requested limit. Items with missing or unparseable prices should not count as verified matches.

I chose 10 out of 10 because price filtering should be a strict requirement rather than something the AI approximates. This would make the shopping experience more reliable and help users trust the recommendations.

---

## Overall Evaluation

For FitFindr AI, I consider the application successful when it can consistently remember selected clothing items, generate readable outfit recommendations, and respect the user's shopping preferences.

The three criteria focus on different parts of the application: state management, AI-generated content quality, and filtering accuracy.

If the application fails any of these tests, I would investigate whether the problem comes from the session state, the AI prompt, or the filtering logic.

In the future, I would also like to improve size filtering, error handling, and recommendations based on the user's existing wardrobe.

My overall goal is to make FitFindr more than just an AI outfit generator. I want it to become a practical tool that helps users discover clothing, stay within their budgets, and make better outfit choices.

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
