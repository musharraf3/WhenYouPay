"""Validation against the worked examples Medicare publishes.

https://www.medicare.gov/prescription-payment-plan/examples

This is the only test file that checks the engine against numbers produced
by someone else. Everything else in the suite checks internal consistency,
which cannot catch a misreading of the regulation. These can.

Two of the three published tables differ from this engine by a few cents in
the final month. In both of those cases the engine's column sums exactly to
the correct annual total and the published one does not, so the difference
is rounding presentation rather than method. The tolerance below is set to
admit exactly that and nothing larger, and each case is asserted to land on
its correct annual total.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whenyoupay.engine import simulate  # noqa: E402

CENT_TOLERANCE = 0.07

# Example 1: $525 a month January through April, enrolled from January.
# Reaches the $2,100 ceiling in April, after which no new costs accrue.
EX1_COSTS = [525.0] * 4 + [0.0] * 8
EX1_PUBLISHED = [175.00, 79.55, 132.05, 190.38] + [190.38] * 8

# Example 2: a steady $80 a month all year, enrolled from January.
EX2_COSTS = [80.0] * 12
EX2_PUBLISHED = [80.00, 7.27, 15.27, 24.16, 34.16, 45.59,
                 58.93, 74.92, 94.93, 121.59, 161.59, 241.53]

# Example 3: $4 a month, a $617 month in April when participation starts,
# and $124 in July and October.
EX3_COSTS = [4.0, 4.0, 4.0, 617.0, 4.0, 4.0, 124.0, 4.0, 4.0, 124.0, 4.0, 4.0]
EX3_PUBLISHED = [4.00, 4.00, 4.00, 232.00, 48.63, 49.20,
                 69.86, 70.66, 71.66, 113.00, 115.00, 118.99]


def _billed(costs, start):
    return [round(x, 2) for x in simulate(costs, 2026, start).billed]


def test_example_1_high_early_costs():
    got = _billed(EX1_COSTS, 1)
    for month, (g, p) in enumerate(zip(got, EX1_PUBLISHED), start=1):
        assert abs(g - p) <= CENT_TOLERANCE, (month, g, p)
    assert abs(sum(got) - 2100.00) < 0.005


def test_example_1_first_month_is_the_threshold_over_twelve():
    """$2,100 / 12 = $175.00 exactly. This single figure confirms that
    'months remaining' includes the month being billed, which is the
    assumption every other number in this repository depends on."""
    assert _billed(EX1_COSTS, 1)[0] == 175.00


def test_example_2_steady_costs():
    got = _billed(EX2_COSTS, 1)
    for month, (g, p) in enumerate(zip(got, EX2_PUBLISHED), start=1):
        assert abs(g - p) <= CENT_TOLERANCE, (month, g, p)
    assert abs(sum(got) - 960.00) < 0.005


def test_example_2_is_the_backfire_and_medicare_publishes_it():
    """The headline finding is not mine. Medicare's own steady-spender
    example ends the year with a December bill more than three times the
    monthly cost at the counter."""
    got = _billed(EX2_COSTS, 1)
    assert got[11] / 80.0 > 3.0
    assert abs(EX2_PUBLISHED[11] / 80.0 - 3.019) < 0.01


def test_example_3_mid_year_start():
    got = _billed(EX3_COSTS, 4)
    for month, (g, p) in enumerate(zip(got, EX3_PUBLISHED), start=1):
        assert abs(g - p) <= 0.005, (month, g, p)   # this one is exact
    assert abs(sum(got) - 901.00) < 0.005


def test_example_3_months_before_election_are_paid_at_the_counter():
    got = _billed(EX3_COSTS, 4)
    assert got[:3] == [4.00, 4.00, 4.00]


def test_half_up_rounding_matches_medicare():
    """Medicare bills $58.925 as $58.93 and $94.925 as $94.93. Banker's
    rounding would give $58.92 and $94.92, and the year would drift."""
    got = _billed(EX2_COSTS, 1)
    assert got[6] == 58.93
    assert got[8] == 94.93
