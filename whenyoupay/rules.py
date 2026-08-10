"""The Medicare Prescription Payment Plan, as written.

Every constant and every rule in this file carries the place it came from.
Nothing here is a judgement call, an estimate, or a model output. If a number
below is wrong, the citation next to it says exactly which document to check.

Primary source: 42 CFR 423.137, "Medicare Prescription Payment Plan",
established by section 11202 of the Inflation Reduction Act of 2022 as
section 1860D-2(b)(2)(E) of the Social Security Act.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- annual out-of-pocket threshold ----------------------------------------
# The Part D annual out-of-pocket threshold, above which the enrollee pays
# nothing further for covered Part D drugs. Indexed annually.
#   2025: $2,000  - first year of both the cap and this program
#   2026: $2,100
OOP_THRESHOLD = {
    2025: 2000.00,
    2026: 2100.00,
}
THRESHOLD_SOURCE = (
    "Social Security Act 1860D-2(b)(4)(B), as amended by IRA sec. 11201; "
    "annual figures published by CMS in the Part D benefit parameters."
)

# --- the timing rules -------------------------------------------------------
# Election and processing: 42 CFR 423.137(d)(1)-(4). Retroactive election:
# (d)(6). Grace period before involuntary termination: (f)(2)(ii) and (f)(3).
PROCESSING_DAYS_BEFORE_YEAR = 10   # requests received before the plan year
PROCESSING_HOURS_DURING_YEAR = 24  # requests received during the plan year
RETROACTIVE_ELECTION_HOURS = 72    # window to ask for a claim to be undone
GRACE_PERIOD_MONTHS = 2            # minimum grace period before termination

RETROACTIVE_TEST = (
    "A retroactive election is available only where the enrollee believes "
    "that delay may seriously jeopardize their life, health, or ability to "
    "regain maximum function, and the request is made within 72 hours of "
    "the date and time the claim was adjudicated. 42 CFR 423.137(d)(6)."
)


@dataclass(frozen=True)
class Rule:
    """A rule with the text that makes it true."""
    key: str
    statement: str
    citation: str


RULES = [
    Rule(
        "first_month_cap",
        "For the first month of participation, the monthly cap is the annual "
        "out-of-pocket threshold minus the out-of-pocket costs already "
        "incurred that year, divided by the number of months remaining in "
        "the plan year.",
        "42 CFR 423.137(c)(1)(i)",
    ),
    Rule(
        "later_month_cap",
        "For each subsequent month, the monthly cap is the sum of any "
        "remaining out-of-pocket costs owed and any additional out-of-pocket "
        "costs incurred, divided by the number of months remaining in the "
        "plan year.",
        "42 CFR 423.137(c)(1)(ii)",
    ),
    Rule(
        "months_remaining_inclusive",
        "The number of months remaining in the plan year includes the month "
        "for which the cap is being calculated.",
        "42 CFR 423.137(c)(3)",
    ),
    Rule(
        "no_cost_reduction",
        "Participation changes when the enrollee pays. It does not change "
        "what the enrollee owes.",
        "42 CFR 423.137(a); SSA 1860D-2(b)(2)(E)",
    ),
    Rule(
        "no_fees_or_interest",
        "A Part D sponsor must not charge late fees, interest payments, or "
        "other fees, such as for different payment mechanisms.",
        "42 CFR 423.137(g)(1)(iii)",
    ),
    Rule(
        "billed_never_exceeds_cap",
        "The amount billed for the month for which the maximum monthly cap "
        "is being calculated cannot be higher than the cap for that month.",
        "42 CFR 423.137(g)(1)(ii)",
    ),
    Rule(
        "retroactive_window",
        RETROACTIVE_TEST,
        "42 CFR 423.137(d)(6)",
    ),
    Rule(
        "grace_period",
        "Before terminating a participant for non-payment, the plan must "
        "give a grace period of at least two months, and the participant "
        "stays in if the overdue balance is paid in full within it.",
        "42 CFR 423.137(f)(2)(ii), (f)(3)",
    ),
    Rule(
        "year_end_balance",
        "Unsettled balances at the end of the plan year are treated as plan "
        "losses. The enrollee's Part D coverage is not forfeited over them.",
        "42 CFR 423.137(g)(4)",
    ),
]

RULES_BY_KEY = {r.key: r for r in RULES}


def threshold(year: int) -> float:
    if year not in OOP_THRESHOLD:
        raise ValueError(
            f"No published out-of-pocket threshold for {year}. "
            f"Known years: {sorted(OOP_THRESHOLD)}. {THRESHOLD_SOURCE}")
    return OOP_THRESHOLD[year]


def cite(key: str) -> str:
    r = RULES_BY_KEY[key]
    return f"{r.statement} [{r.citation}]"
