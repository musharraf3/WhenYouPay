"""Month-by-month simulation of the Medicare Prescription Payment Plan.

Deterministic arithmetic, straight from 42 CFR 423.137. No model touches a
number anywhere in this file, and none should. The only thing a language
model is good for in this program is explaining, afterwards, what the code
already worked out.

One invariant governs everything and is tested: the total the enrollee pays
across the year is identical whether or not they participate. The program
moves money between months. It does not remove any.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .rules import threshold

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


@dataclass
class MonthResult:
    month: int
    out_of_pocket_incurred: float   # what the pharmacy counter would charge
    billed: float                   # what the enrollee actually pays
    unpaid_balance: float           # carried into next month
    months_remaining: int
    participating: bool

    @property
    def name(self) -> str:
        return MONTHS[self.month - 1]


@dataclass
class Outcome:
    year: int
    start_month: int | None
    months: list[MonthResult] = field(default_factory=list)

    @property
    def billed(self) -> list[float]:
        return [m.billed for m in self.months]

    @property
    def counter(self) -> list[float]:
        return [m.out_of_pocket_incurred for m in self.months]

    @property
    def total_billed(self) -> float:
        return sum(self.billed)

    @property
    def total_counter(self) -> float:
        return sum(self.counter)

    @property
    def worst_month(self) -> float:
        return max(self.billed) if self.billed else 0.0

    @property
    def year_end_unpaid(self) -> float:
        """A balance can still be outstanding on 31 December, and joining in
        the last month or two is how that happens. The regulation addresses
        it directly: unsettled balances are treated as plan losses, and the
        enrollee does not forfeit coverage over them. 42 CFR 423.137(g)(4).

        Conservation therefore reads: billed + still-owed == counter total.
        """
        return self.months[-1].unpaid_balance if self.months else 0.0

    @property
    def total_accounted(self) -> float:
        return self.total_billed + self.year_end_unpaid

    def months_worse_than_counter(self, tol: float = 0.005) -> list[int]:
        """Months where participating costs MORE than paying at the counter.

        These exist, they are not a bug, and they are the reason this tool
        will tell some people not to enrol.
        """
        return [m.month for m in self.months
                if m.billed > m.out_of_pocket_incurred + tol]


def _cap_first_month(year: int, incurred_before: float,
                     months_remaining: int) -> float:
    """(annual threshold - already incurred) / months remaining.

    42 CFR 423.137(c)(1)(i). Months remaining includes the current month,
    per 42 CFR 423.137(c)(3).
    """
    return max(0.0, threshold(year) - incurred_before) / months_remaining


def _cents(x: float) -> float:
    """Bills are issued in whole cents, and the balance carried forward is
    the rounded one rather than the exact one. Keeping full precision drifts
    by a few cents come December, which is small but matters: matching the
    worked examples Medicare publishes is how anyone checks this code.

    Half-up, not banker's rounding. Medicare's own example bills $58.925 as
    $58.93 and $94.925 as $94.93, which settles the question.
    """
    return float(Decimal(repr(x)).quantize(Decimal("0.01"),
                                           rounding=ROUND_HALF_UP))


def simulate(monthly_out_of_pocket: list[float], year: int = 2026,
             start_month: int | None = 1) -> Outcome:
    """Run a year.

    `monthly_out_of_pocket` is twelve numbers: what this person would pay at
    the pharmacy counter each month with no program at all.

    Those numbers are clamped to the annual out-of-pocket maximum as the year
    accumulates. Once an enrollee reaches the threshold they pay nothing more
    for covered Part D drugs, at the counter or in the program, so a caller
    who passes $500 a month is asking about someone who stops paying in May.
    Taking the input literally would report $6,000 for a year that costs
    $2,100 -- and would contradict the ceiling this tool prints in its own
    advice. See `threshold()` and SSA 1860D-2(b)(4)(B).

    `start_month` is the month participation begins, 1-12, or None to model
    not participating. Costs incurred before `start_month` are paid at the
    counter, which is the rule that makes the whole thing so sensitive to
    when someone finds out the program exists.
    """
    if len(monthly_out_of_pocket) != 12:
        raise ValueError("expected twelve monthly amounts")
    if any(x < 0 for x in monthly_out_of_pocket):
        raise ValueError("out-of-pocket amounts cannot be negative")
    if start_month is not None and not 1 <= start_month <= 12:
        raise ValueError("start_month must be 1-12 or None")

    out = Outcome(year=year, start_month=start_month)
    unpaid = 0.0
    incurred = 0.0

    for m in range(1, 13):
        # The ceiling is applied here, before either path sees the number, so
        # the counter and the program clamp identically. That is what keeps
        # the conservation invariant true above the threshold as well as below
        # it: both sides are spreading the same capped total.
        oop = min(float(monthly_out_of_pocket[m - 1]),
                  max(0.0, threshold(year) - incurred))
        remaining = 12 - m + 1
        participating = start_month is not None and m >= start_month

        if not participating:
            billed = oop
        elif m == start_month:
            # 42 CFR 423.137(c)(1)(i). A participant is never billed more
            # than they actually incurred, even when the cap is higher.
            billed = min(oop, _cap_first_month(year, incurred, remaining))
        else:
            # 42 CFR 423.137(c)(1)(ii).
            billed = (unpaid + oop) / remaining

        billed = _cents(billed)
        unpaid = _cents(unpaid + oop - billed)
        incurred += oop
        out.months.append(MonthResult(
            month=m, out_of_pocket_incurred=oop, billed=billed,
            unpaid_balance=unpaid, months_remaining=remaining,
            participating=participating,
        ))

    return out


def compare(monthly_out_of_pocket: list[float], year: int = 2026,
            start_month: int = 1) -> dict:
    """Participating against not, on the same costs."""
    joined = simulate(monthly_out_of_pocket, year, start_month)
    counter = simulate(monthly_out_of_pocket, year, None)
    return {
        "joined": joined,
        "counter": counter,
        "worst_month_counter": counter.worst_month,
        "worst_month_joined": joined.worst_month,
        "worst_month_relief": counter.worst_month - joined.worst_month,
        "months_worse": joined.months_worse_than_counter(),
        "total_counter": counter.total_counter,
        "total_joined": joined.total_billed,
        "year_end_unpaid": joined.year_end_unpaid,
    }
