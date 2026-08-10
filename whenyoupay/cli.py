"""Command line entry point."""
from __future__ import annotations

import argparse
import json

from .advise import advise
from .engine import MONTHS, compare, simulate
from .profiles import PROFILES


def _parse_costs(s: str) -> list[float]:
    parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
    if len(parts) == 1:
        return [float(parts[0])] * 12
    if len(parts) != 12:
        raise argparse.ArgumentTypeError(
            "give one number (same every month) or twelve")
    return [float(p) for p in parts]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="whenyoupay",
        description="What the Medicare Prescription Payment Plan would do "
                    "to your year. It changes when you pay, never how much.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--costs", type=_parse_costs,
                     help="twelve monthly out-of-pocket amounts, or one")
    src.add_argument("--profile", choices=sorted(PROFILES))
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--join", type=int, default=1, metavar="MONTH",
                   help="month you join, 1-12 (default January)")
    p.add_argument("--already-paid", type=float, default=0.0,
                   help="already paid at the counter this year")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    costs = a.costs if a.costs else PROFILES[a.profile][0]
    c = compare(costs, a.year, a.join)
    adv = advise(costs, a.year, a.join, a.already_paid)

    if a.json:
        print(json.dumps({
            "verdict": adv.verdict,
            "headline": adv.headline,
            "counter": c["counter"].counter,
            "billed": c["joined"].billed,
            "worst_month_counter": c["worst_month_counter"],
            "worst_month_joined": c["worst_month_joined"],
            "months_worse": c["months_worse"],
            "total_counter": c["total_counter"],
            "total_joined": c["total_joined"],
        }, indent=2))
        return 0

    print(f"{'month':11s} {'at the counter':>15s} {'in the program':>18s}")
    for m in c["joined"].months:
        flag = "  <- more" if m.billed > m.out_of_pocket_incurred + 0.005 else ""
        print(f"{MONTHS[m.month - 1]:11s} {m.out_of_pocket_incurred:15,.2f} "
              f"{m.billed:18,.2f}{flag}")
    print(f"{'total':11s} {c['total_counter']:15,.2f} "
          f"{c['total_joined']:18,.2f}")
    print()
    print(adv.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
