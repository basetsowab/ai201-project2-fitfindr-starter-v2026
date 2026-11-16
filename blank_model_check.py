"""
Diagnostic for the improvement: what reaches the user when the model answers
with an empty string at the fit-card step?

The five criteria never saw this happen, because the model never came back
blank in 41 runs. So this forces it: `generate` is replaced, for the
create_fit_card call only, with one that returns "". Everything else is real.

    python blank_model_check.py
"""

import config  # noqa: F401  (UTF-8 console on Windows)
import checks
import tools
from agent import run_agent
from utils.data_loader import get_example_wardrobe

QUERIES = ["vintage graphic tee under $30", "denim jacket under $50", "corduroy pants",
           "suede chelsea boots", "linen blazer"]

real_generate = tools.generate


def blank_for_fit_card(prompt, system=None, **kw):
    if "caption" in prompt.lower():
        return ""
    return real_generate(prompt, system=system, **kw)


tools.generate = blank_for_fit_card
passes = 0
for q in QUERIES:
    s = run_agent(q, get_example_wardrobe())
    ok, why = checks.c1_completes(s)
    passes += ok
    print(f"{'PASS' if ok else 'FAIL'}  {q!r:34} fit_card={s['fit_card']!r:.70}")
print(f"\ncriterion 1 rule with a blank model at the fit-card step: {passes}/{len(QUERIES)}")
