"""Reproduce every number in the README. One command, no network, no key.

Nothing here is a dataset. Every figure is the regulation's own arithmetic
applied to a stated cost shape, so anyone can check it with a calculator and
a copy of 42 CFR 423.137.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whenyoupay.advise import advise                    # noqa: E402
from whenyoupay.engine import MONTHS, compare, simulate  # noqa: E402
from whenyoupay.profiles import PROFILES                 # noqa: E402
from whenyoupay.rules import threshold                   # noqa: E402

YEAR = 2026
CENT = 0.005


def invariant_check() -> dict:
    """The claim the whole tool rests on: participation never changes the
    total. Checked over every profile and every possible joining month."""
    worst = 0.0
    checked = 0
    for costs, _d in PROFILES.values():
        for start in range(1, 13):
            j = simulate(costs, YEAR, start)
            b = simulate(costs, YEAR, None).total_billed
            worst = max(worst, abs(j.total_accounted - b))
            checked += 1
    return {"combinations_checked": checked,
            "largest_total_difference": round(worst, 10),
            "holds": worst < CENT}


def profile_table() -> list[dict]:
    rows = []
    for name, (costs, desc) in PROFILES.items():
        c = compare(costs, YEAR, 1)
        a = advise(costs, YEAR, 1)
        rows.append({
            "profile": name, "description": desc,
            "annual_total": round(c["total_counter"], 2),
            "worst_month_counter": round(c["worst_month_counter"], 2),
            "worst_month_joined": round(c["worst_month_joined"], 2),
            "relief": round(c["worst_month_relief"], 2),
            "months_worse_than_counter": len(c["months_worse"]),
            "december_bill": round(c["joined"].billed[11], 2),
            "verdict": a.verdict,
        })
    return rows


def shock_month_sweep() -> list[dict]:
    """The best case anyone can have: an expensive drug starts, and the
    person enrols in that same month. Nothing is late, nobody made a
    mistake. The only thing that changes is where in the calendar the shock
    lands."""
    rows = []
    for m in range(1, 13):
        costs = [25.0] * 12
        costs[m - 1] = 1800.0
        c = compare(costs, YEAR, m)
        rows.append({
            "shock_month": MONTHS[m - 1],
            "months_to_spread_over": 12 - m + 1,
            "worst_month": round(c["worst_month_joined"], 2),
            "relief": round(c["worst_month_relief"], 2),
            "relief_share": round(c["worst_month_relief"] / 1800.0, 4),
            "year_end_unpaid": round(c["year_end_unpaid"], 2),
            "verdict": advise(costs, YEAR, m).verdict,
        })
    return rows


def found_out_late_sweep() -> list[dict]:
    """The shock lands in January and is paid at the counter. Then the
    person hears about the programme. This is the sweep that shows why the
    72-hour retroactive window is the whole ballgame."""
    costs = PROFILES["january_shock"][0]
    rows = []
    for start in range(1, 13):
        c = compare(costs, YEAR, start)
        rows.append({
            "join_month": MONTHS[start - 1],
            "worst_month": round(c["worst_month_joined"], 2),
            "relief": round(c["worst_month_relief"], 2),
            "verdict": advise(costs, YEAR, start).verdict,
        })
    return rows


def flat_backfire() -> list[dict]:
    """For someone whose costs are already flat, the programme has nothing
    to smooth, so the balance simply migrates to the end of the year."""
    rows = []
    for monthly in (20, 40, 60, 100, 150, 200):
        costs = [float(monthly)] * 12
        c = compare(costs, YEAR, 1)
        dec = c["joined"].billed[11]
        rows.append({
            "monthly_at_counter": monthly,
            "december_bill": round(dec, 2),
            "multiple_of_counter": round(dec / monthly, 2),
            "months_worse_than_counter": len(c["months_worse"]),
            "verdict": advise(costs, YEAR, 1).verdict,
        })
    return rows


def main() -> int:
    out = {
        "year": YEAR,
        "annual_out_of_pocket_threshold": threshold(YEAR),
        "invariant": invariant_check(),
        "profiles": profile_table(),
        "shock_month_sweep": shock_month_sweep(),
        "found_out_late_sweep": found_out_late_sweep(),
        "flat_backfire": flat_backfire(),
    }
    os.makedirs("results", exist_ok=True)
    with open("results/results.json", "w") as f:
        json.dump(out, f, indent=2)

    inv = out["invariant"]
    print("=" * 72)
    print("invariant: participation never changes the annual total")
    print("=" * 72)
    print(f"  {inv['combinations_checked']} profile/start-month combinations, "
          f"largest difference ${inv['largest_total_difference']}")
    print(f"  holds: {inv['holds']}\n")

    print("=" * 72)
    print("joining in January, by shape of the year")
    print("=" * 72)
    print(f"{'profile':16s} {'worst month':>12s} {'joined':>9s} {'relief':>9s} "
          f"{'Dec':>9s}  verdict")
    for r in out["profiles"]:
        print(f"{r['profile']:16s} {r['worst_month_counter']:12,.0f} "
              f"{r['worst_month_joined']:9,.0f} {r['relief']:9,.0f} "
              f"{r['december_bill']:9,.0f}  {r['verdict']}")

    print("\n" + "=" * 72)
    print("an $1,800 drug starts, and you enrol the same month. nothing late.")
    print("=" * 72)
    print(f"{'shock lands':12s} {'months left':>12s} {'worst month':>12s} "
          f"{'relief':>9s} {'% of shock':>11s}  verdict")
    for r in out["shock_month_sweep"]:
        print(f"{r['shock_month']:12s} {r['months_to_spread_over']:12d} "
              f"{r['worst_month']:12,.0f} {r['relief']:9,.0f} "
              f"{r['relief_share']:11.0%}  {r['verdict']}")

    print("\n" + "=" * 72)
    print("$1,800 paid at the counter in January, then you hear about it")
    print("=" * 72)
    print(f"{'joined in':12s} {'worst month':>12s} {'relief':>9s}  verdict")
    for r in out["found_out_late_sweep"]:
        print(f"{r['join_month']:12s} {r['worst_month']:12,.0f} "
              f"{r['relief']:9,.0f}  {r['verdict']}")

    print("\n" + "=" * 72)
    print("already-flat costs: what the programme does to December")
    print("=" * 72)
    print(f"{'per month':>10s} {'December':>10s} {'multiple':>10s}  verdict")
    for r in out["flat_backfire"]:
        print(f"{r['monthly_at_counter']:10,.0f} {r['december_bill']:10,.2f} "
              f"{r['multiple_of_counter']:9.1f}x  {r['verdict']}")

    print("\nresults/results.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
