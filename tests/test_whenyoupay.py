import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whenyoupay.advise import advise                        # noqa: E402
from whenyoupay.engine import compare, simulate             # noqa: E402
from whenyoupay.profiles import PROFILES                    # noqa: E402
from whenyoupay.rules import (OOP_THRESHOLD, RULES,         # noqa: E402
                              RULES_BY_KEY, cite, threshold)

CENT = 0.005
FLAT = [60.0] * 12
SHOCK = [1800.0] + [25.0] * 11


# --- the invariant ----------------------------------------------------------

def test_participation_never_changes_the_total():
    """The claim the whole tool rests on. Money moves between months; none
    of it disappears. Anything still owed on 31 December counts."""
    for costs, _d in PROFILES.values():
        counter = simulate(costs, 2026, None).total_billed
        for start in range(1, 13):
            joined = simulate(costs, 2026, start)
            assert abs(joined.total_accounted - counter) < CENT


def test_everything_incurred_is_billed_by_december():
    """No balance survives the year end in this model, and that is correct.

    December divides by one remaining month, so whatever is left is billed in
    full. An earlier version of this test asserted the opposite, and passed --
    but only because the engine was not applying the annual ceiling. Once
    incurred costs ran past the threshold, `_cap_first_month` went negative,
    was floored to zero, and a late joiner was billed nothing while carrying a
    balance that could not exist.

    42 CFR 423.137(g)(4) is still cited and still real: it governs unsettled
    balances, which arise from non-*payment*. This engine models what a plan
    bills, not what an enrollee has paid, so it cannot produce one.
    """
    shapes = [c for c, _d in PROFILES.values()]
    shapes += [[500.0] * 12, [0.0] * 11 + [3000.0], [175.0] * 12]
    for costs in shapes:
        for start in list(range(1, 13)) + [None]:
            assert simulate(costs, 2026, start).year_end_unpaid == 0.0


# --- the annual out-of-pocket ceiling ---------------------------------------

def test_costs_above_the_ceiling_stop_accruing():
    """A Part D enrollee pays nothing more for covered drugs once they reach
    the annual threshold. Taking a caller's $500 a month literally would
    report $6,000 for a year that costs $2,100 -- and would contradict the
    ceiling this tool prints in its own advice."""
    joined = simulate([500.0] * 12, 2026, 1)
    counter = simulate([500.0] * 12, 2026, None)
    assert abs(counter.total_counter - threshold(2026)) < CENT
    assert abs(joined.total_billed - threshold(2026)) < CENT


def test_the_ceiling_applies_to_the_counter_too():
    """Both paths clamp identically. If only the program side stopped at the
    threshold, the tool would invent relief that does not exist."""
    for monthly in (200.0, 300.0, 500.0):
        joined = simulate([monthly] * 12, 2026, 1)
        counter = simulate([monthly] * 12, 2026, None)
        assert abs(joined.total_billed - counter.total_counter) < CENT


def test_conservation_holds_above_the_ceiling():
    """The 96-case sweep only used profiles that stay under the threshold,
    which is why the invariant looked healthy while the ceiling was ignored."""
    for costs in ([500.0] * 12, [3000.0] * 12, [0.0] * 10 + [2000.0, 2000.0]):
        counter = simulate(costs, 2026, None).total_billed
        for start in range(1, 13):
            joined = simulate(costs, 2026, start)
            assert abs(joined.total_accounted - counter) < CENT


def test_no_month_is_negative():
    for costs, _d in PROFILES.values():
        for start in range(1, 13):
            assert all(b >= -CENT for b in simulate(costs, 2026, start).billed)


# --- the formula ------------------------------------------------------------

def test_first_month_cap_matches_the_regulation():
    """(threshold - incurred) / months remaining, inclusive of this month."""
    out = simulate(SHOCK, 2026, 1)
    assert abs(out.billed[0] - 2100.0 / 12) < CENT


def test_months_remaining_includes_the_current_month():
    """Joining in December leaves one month, not zero."""
    out = simulate([0.0] * 11 + [120.0], 2026, 12)
    assert out.months[11].months_remaining == 1


def test_later_months_are_balance_plus_new_over_months_left():
    out = simulate(SHOCK, 2026, 1)
    unpaid_after_jan = out.months[0].unpaid_balance
    expected_feb = (unpaid_after_jan + 25.0) / 11
    assert abs(out.billed[1] - expected_feb) < CENT


def test_joining_later_leaves_earlier_months_at_counter_price():
    out = simulate(SHOCK, 2026, 6)
    assert out.billed[0] == 1800.0
    assert out.months[0].participating is False


def test_the_current_year_is_supported():
    """This repository has an expiry date and nothing else would announce it.

    OOP_THRESHOLD is a published figure, not a formula -- it is set annually by
    CMS and cannot be derived. `threshold()` refuses unknown years rather than
    guessing, which is right, but it means that on 1 January of the first
    unlisted year every answer for the current year becomes an exception.

    Same instinct as the code-set vintage gate in WhoCounts: a constant that
    ages out silently should set off an alarm before a user finds it. Green
    today; red the day CMS publishes the next threshold and this file has not
    been updated.
    """
    year = datetime.date.today().year
    assert year in OOP_THRESHOLD, (
        f"No out-of-pocket threshold on file for {year}. CMS publishes it "
        f"annually; add it to OOP_THRESHOLD in whenyoupay/rules.py with its "
        f"source. Known years: {sorted(OOP_THRESHOLD)}.")


def test_unknown_year_refuses_rather_than_guessing():
    with pytest.raises(ValueError):
        threshold(2031)


def test_thresholds_are_the_published_ones():
    assert OOP_THRESHOLD[2025] == 2000.00
    assert OOP_THRESHOLD[2026] == 2100.00


def test_input_validation():
    with pytest.raises(ValueError):
        simulate([10.0] * 11, 2026, 1)
    with pytest.raises(ValueError):
        simulate([-1.0] * 12, 2026, 1)
    with pytest.raises(ValueError):
        simulate([10.0] * 12, 2026, 13)


# --- the findings -----------------------------------------------------------

def test_a_big_early_bill_is_what_the_program_is_for():
    c = compare(SHOCK, 2026, 1)
    assert c["worst_month_counter"] == 1800.0
    assert c["worst_month_joined"] < 250
    assert advise(SHOCK, 2026, 1).verdict == "helps"


def test_flat_costs_backfire_and_the_tool_says_so():
    """Someone whose costs are already level has nothing to smooth. The
    balance simply migrates to the end of the year."""
    c = compare(FLAT, 2026, 1)
    assert c["worst_month_joined"] > c["worst_month_counter"]
    assert c["joined"].billed[11] > 3 * FLAT[0]
    assert advise(FLAT, 2026, 1).verdict == "does not help"


def test_the_flat_december_multiple_peaks_at_the_threshold_over_twelve():
    """Below threshold/12 the multiple is constant whatever the amount: it
    falls out of the arithmetic, not out of anyone's income.

    Above it the multiple *falls*, and steeply. This is the opposite of what
    this test asserted before the ceiling was enforced. Spending more than
    threshold/12 a month means reaching the annual maximum partway through the
    year and paying nothing after it, so December has less left to absorb.

    The worst case is therefore not the biggest spender. It is whoever spends
    almost exactly the threshold divided by twelve -- $175 a month in 2026 --
    which is the only amount that both stays flat all year and reaches the
    ceiling on the last day of it.
    """
    below = []
    for monthly in (20.0, 60.0, 150.0):        # under 2100/12 = 175
        c = compare([monthly] * 12, 2026, 1)
        below.append(c["joined"].billed[11] / monthly)
    assert max(below) - min(below) < 0.01
    assert 3.0 < below[0] < 3.05

    peak = compare([175.0] * 12, 2026, 1)["joined"].billed[11] / 175.0
    assert abs(peak - below[0]) < 0.01

    previous = peak
    for monthly in (200.0, 300.0, 500.0):
        multiple = compare([monthly] * 12, 2026, 1)["joined"].billed[11] / monthly
        assert multiple < previous, (monthly, multiple, previous)
        previous = multiple


def test_relief_falls_as_the_shock_lands_later():
    """Enrolling the same month the drug starts, every time. Nobody is late.
    The protection still shrinks, because the calendar decides it."""
    reliefs = []
    for m in range(1, 13):
        costs = [25.0] * 12
        costs[m - 1] = 1800.0
        reliefs.append(compare(costs, 2026, m)["worst_month_relief"])
    assert reliefs == sorted(reliefs, reverse=True)
    assert reliefs[0] > 1500
    assert reliefs[11] == 0


def test_money_already_paid_at_the_counter_cannot_be_recovered():
    c = compare(SHOCK, 2026, 2)
    assert c["worst_month_joined"] == 1800.0
    assert c["worst_month_relief"] == 0.0


# --- what it says -----------------------------------------------------------

def test_it_never_claims_to_save_money():
    for costs, _d in PROFILES.values():
        a = advise(costs, 2026, 1)
        text = " ".join([a.headline] + a.detail + a.warnings).lower()
        for word in ("save", "savings", "cheaper", "discount", "reduce your "
                                                              "costs"):
            assert word not in text, word


def test_every_advice_states_the_total_is_unchanged():
    for costs, _d in PROFILES.values():
        a = advise(costs, 2026, 1)
        assert any("same either way" in d for d in a.detail)


def test_it_declines_to_recommend_when_it_would_not_help():
    a = advise(FLAT, 2026, 1)
    assert a.verdict == "does not help"
    assert "do not join" in a.headline.lower()


def test_it_warns_about_extra_help_every_time():
    for costs, _d in PROFILES.values():
        a = advise(costs, 2026, 1)
        assert any("Extra Help" in w for w in a.warnings)


def test_counter_payments_trigger_the_72_hour_warning():
    a = advise(SHOCK, 2026, 2, already_paid_at_counter=1800.0)
    joined = " ".join(a.warnings)
    assert "72 hours" in joined
    assert any("423.137(c)" in c for c in a.citations)


def test_the_helpful_case_frames_later_months_as_a_trade_not_an_alarm():
    a = advise(SHOCK, 2026, 1)
    assert a.verdict == "helps"
    assert any("good one" in d for d in a.detail)
    assert not any("would pay more than the counter" in w for w in a.warnings)


# --- provenance -------------------------------------------------------------

def test_every_rule_carries_a_citation():
    assert RULES
    for r in RULES:
        assert r.citation.strip()
        assert "423.137" in r.citation or "IRA" in r.citation
        assert r.statement.strip().endswith(".")


def test_cite_renders_statement_and_source():
    s = cite("months_remaining_inclusive")
    assert "includes the month" in s
    assert "42 CFR 423.137" in s


def test_advice_citations_are_all_real_rules():
    known = {cite(k) for k in RULES_BY_KEY}
    for costs, _d in PROFILES.values():
        for c in advise(costs, 2026, 1).citations:
            assert c in known


# ---------------------------------------------------------------------------
# Citation pinning.
#
# The paragraph numbers in this repository have been wrong once already: an
# early draft cited the cap formula to 423.137(d)(2), and a stale (d)(2)(i)
# survived in engine.py long after the README was corrected. A citation that
# is merely well-formed is not a citation that is right, and the existing test
# only checks that emitted citations exist in rules.py.
#
# Each pairing below was read off the regulation itself (eCFR / Cornell LII),
# not inferred. If someone renumbers one, this fails instead of shipping a
# confident wrong reference in a post that trades on citing primary sources.
# ---------------------------------------------------------------------------

EXPECTED_CITATIONS = {
    "first_month_cap":           "42 CFR 423.137(c)(1)(i)",
    "later_month_cap":           "42 CFR 423.137(c)(1)(ii)",
    "months_remaining_inclusive": "42 CFR 423.137(c)(3)",
    "retroactive_window":        "42 CFR 423.137(d)(6)",
    "grace_period":              "42 CFR 423.137(f)(2)(ii), (f)(3)",
    "year_end_balance":          "42 CFR 423.137(g)(4)",
    "no_fees_or_interest":       "42 CFR 423.137(g)(1)(iii)",
    "billed_never_exceeds_cap":  "42 CFR 423.137(g)(1)(ii)",
}


def test_citations_match_the_regulation():
    from whenyoupay.rules import RULES_BY_KEY
    for key, citation in EXPECTED_CITATIONS.items():
        assert key in RULES_BY_KEY, f"rule '{key}' has gone missing"
        assert RULES_BY_KEY[key].citation == citation, (
            f"{key}: expected {citation}, found {RULES_BY_KEY[key].citation}")


def test_no_source_file_cites_the_retired_paragraphs():
    """(d)(2) was the original mistake. It must not come back anywhere."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    for path in list((root / "whenyoupay").glob("*.py")) + [root / "README.md"]:
        text = path.read_text(encoding="utf-8")
        assert "423.137(d)(2)" not in text, f"{path.name} cites retired 423.137(d)(2)"
