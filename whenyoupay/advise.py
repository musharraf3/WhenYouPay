"""What to tell the person, and when to tell them not to bother.

A tool that recommends enrollment to everyone is a brochure. This one has to
be able to say "this will not help you, and in November it will cost you
more than the counter would have", because for a large class of people that
is the true answer.

Three rules hold everywhere in this module:

  1. It never claims the program saves money. It cannot. The total is
     arithmetically identical and that is asserted in a test.
  2. Every statement that rests on the regulation carries the citation.
  3. When the answer depends on a fact the tool does not have - whether
     someone qualifies for Extra Help, whether a shock is coming - it says
     so instead of guessing in the direction of enrollment.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import MONTHS, compare
from .rules import (GRACE_PERIOD_MONTHS, PROCESSING_DAYS_BEFORE_YEAR,
                    PROCESSING_HOURS_DURING_YEAR, RETROACTIVE_ELECTION_HOURS,
                    cite, threshold)

# Below this much relief in the worst month, the program is not doing
# anything a person would notice, and saying so is more useful than a
# technically-correct yes. A judgement call, stated openly, and the only
# one in the file.
MEANINGFUL_RELIEF = 50.00


@dataclass
class Advice:
    verdict: str            # "helps", "does not help", "too late to help"
    headline: str
    detail: list[str]
    warnings: list[str]
    citations: list[str]

    def render(self) -> str:
        lines = [self.headline, ""]
        lines += [f"  {d}" for d in self.detail]
        if self.warnings:
            lines += [""] + [f"  ! {w}" for w in self.warnings]
        lines += ["", "  Rules this rests on:"]
        lines += [f"    - {c}" for c in self.citations]
        return "\n".join(lines)


def advise(monthly_out_of_pocket: list[float], year: int = 2026,
           start_month: int = 1,
           already_paid_at_counter: float = 0.0) -> Advice:
    c = compare(monthly_out_of_pocket, year, start_month)
    joined, counter = c["joined"], c["counter"]
    relief = c["worst_month_relief"]
    worse = c["months_worse"]

    detail = [
        f"Your costs are the same either way: ${c['total_counter']:,.2f} "
        f"for the year, with or without the program.",
        f"Worst single month at the pharmacy counter: "
        f"${c['worst_month_counter']:,.2f}.",
        f"Worst single month if you join in {MONTHS[start_month - 1]}: "
        f"${c['worst_month_joined']:,.2f}.",
    ]
    citations = [cite("no_cost_reduction"), cite("months_remaining_inclusive")]
    warnings: list[str] = []
    notes: list[str] = []

    # Later months costing more than the counter is not by itself a problem.
    # It is the mechanism: a big month gets pushed into small ones. It only
    # becomes a warning when the person did not get real relief in exchange,
    # which is why this is decided after the verdict rather than before it.
    overshoot = 0.0
    if worse:
        overshoot = max(joined.months[m - 1].billed
                        - joined.months[m - 1].out_of_pocket_incurred
                        for m in worse)
        citations.append(cite("later_month_cap"))

    if already_paid_at_counter > 0:
        warnings.append(
            f"You have already paid ${already_paid_at_counter:,.2f} at the "
            f"counter this year. That money does not enter the program. "
            f"Undoing a claim is possible only within "
            f"{RETROACTIVE_ELECTION_HOURS} hours of the claim being "
            f"adjudicated, and only on health-jeopardy grounds.")
        citations.append(cite("retroactive_window"))

    if relief < MEANINGFUL_RELIEF and not worse:
        verdict = "does not help"
        headline = ("Joining would not change anything you would notice. "
                    "Your costs are already spread.")
    elif relief < MEANINGFUL_RELIEF and worse:
        verdict = "does not help"
        headline = ("Do not join on these numbers. It would not lower your "
                    "worst month and it would raise your later ones.")
    elif start_month > 1 and relief < c["worst_month_counter"] * 0.25:
        verdict = "too late to help"
        headline = (
            f"Joining in {MONTHS[start_month - 1]} recovers little. The "
            f"program can only spread costs you have not yet paid, and "
            f"most of yours are behind you.")
    else:
        verdict = "helps"
        headline = (
            f"Joining lowers your worst month from "
            f"${c['worst_month_counter']:,.2f} to "
            f"${c['worst_month_joined']:,.2f}. You still owe the same "
            f"${c['total_counter']:,.2f} across the year.")

    if worse:
        names = ", ".join(MONTHS[m - 1] for m in worse)
        line = (f"In {names} you would pay more than the counter would have "
                f"charged, by up to ${overshoot:,.2f}, because the balance "
                f"rolls forward into fewer and fewer remaining months.")
        if verdict == "helps":
            notes.append(line + " That is the trade you are making, and on "
                                "these numbers it is a good one.")
        else:
            warnings.append(line)

    detail.extend(notes)
    detail.append(
        f"The {year} out-of-pocket ceiling is ${threshold(year):,.2f}; above "
        f"it you pay nothing more for covered Part D drugs.")
    detail.append(
        f"A request made before the plan year must be processed within "
        f"{PROCESSING_DAYS_BEFORE_YEAR} days; one made during the year, "
        f"within {PROCESSING_HOURS_DURING_YEAR} hours.")

    warnings.append(
        f"Missing a payment does not end your drug coverage. The plan must "
        f"give at least {GRACE_PERIOD_MONTHS} months' grace, and paying the "
        f"overdue balance within it keeps you in.")
    citations.append(cite("grace_period"))

    warnings.append(
        "This tool does not know whether you qualify for Extra Help "
        "(the Part D low-income subsidy). If you do, your copays are "
        "already small and this program has little left to smooth. "
        "Check that first - it lowers what you owe, which this never does.")

    return Advice(verdict=verdict, headline=headline, detail=detail,
                  warnings=warnings, citations=citations)
