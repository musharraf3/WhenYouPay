#!/usr/bin/env python3
"""Run WhenYouPay. No install, no dependencies, no arguments needed.

    python run.py

That is the whole setup. This file adds its own directory to `sys.path`, so it
works from a fresh `git clone` on any Python 3.10 or newer, with nothing
installed and no network. Run it from anywhere:

    python /wherever/WhenYouPay/run.py

It prints the three things the project exists to show:

    1. the program working  — a $1,800 January drug, spread
    2. the calendar          — the same drug, started in each of twelve months
    3. the backfire          — steady costs, and the December bill that follows

Optional, if you want your own numbers rather than the demonstration:

    python run.py --costs 60                 # $60 every month
    python run.py --costs "1800 25 25 ..."   # twelve amounts
    python run.py --profile november_shock --join 11
    python run.py --json

Nothing here computes anything itself. Every figure comes from `whenyoupay/`,
which is the same code the tests and the committed results run against.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _safe_stdout() -> None:
    """Never die on the terminal's encoding.

    Output here is deliberately ASCII, but a redirect or an unusual locale can
    still narrow what stdout accepts. Replacing an unencodable character is
    always better than aborting a report halfway through.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                   # noqa: BLE001
        pass


def _require_python() -> None:
    """Fail with a sentence a person can act on, not a SyntaxError traceback."""
    if sys.version_info < (3, 10):
        sys.exit(
            f"WhenYouPay needs Python 3.10 or newer; this is "
            f"{sys.version.split()[0]}. Nothing else is required — no pip "
            f"install, no dependencies.")


def _demo() -> int:
    """The default run: the whole argument, in one screen of output."""
    from whenyoupay.advise import advise
    from whenyoupay.engine import compare, simulate
    from whenyoupay.profiles import JANUARY_SHOCK
    from whenyoupay.rules import threshold

    year = 2026
    rule = "42 CFR 423.137 - Medicare Prescription Payment Plan"
    print("=" * 74)
    print("WhenYouPay: what the Medicare Prescription Payment Plan does to a year")
    print(f"{rule} | {year} out-of-pocket cap ${threshold(year):,.0f}")
    print("=" * 74)

    # ---- 1. the case the program was built for
    print("\n1. AN EXPENSIVE DRUG STARTS IN JANUARY\n")
    c = compare(JANUARY_SHOCK, year, 1)
    print(f"   At the pharmacy counter, the worst month is "
          f"${c['worst_month_counter']:,.2f}.")
    print(f"   Inside the program it is ${c['worst_month_joined']:,.2f}.")
    print(f"   Either way the year costs ${c['total_counter']:,.2f}. "
          f"Nothing is forgiven.")

    # ---- 2. the calendar
    print("\n2. THE SAME DRUG, STARTED IN A DIFFERENT MONTH\n")
    print("   They join the month it starts every time. Nobody is late.\n")
    print(f"   {'starts':<10}{'worst month':>14}{'vs counter':>14}")
    print("   " + "-" * 38)
    for m in range(1, 13):
        costs = [25.0] * 12
        costs[m - 1] = 1800.0
        cm = compare(costs, year, m)
        share = cm["worst_month_relief"] / cm["worst_month_counter"]
        name = simulate(costs, year, m).months[m - 1].name
        print(f"   {name:<10}{cm['worst_month_joined']:>14,.2f}{share:>13.0%}")
    print("\n   The formula divides by the months that happen to be left, so")
    print("   protection is handed out by the date on the prescription.")

    # ---- 3. the backfire
    print("\n3. WHEN COSTS WERE ALREADY FLAT\n")
    print(f"   {'per month':<12}{'December bill':>16}{'multiple':>11}")
    print("   " + "-" * 39)
    for monthly in (20.0, 60.0, 150.0, 175.0, 200.0, 500.0):
        cf = compare([monthly] * 12, year, 1)
        dec = cf["joined"].billed[11]
        print(f"   ${monthly:<11,.0f}{dec:>16,.2f}{dec / monthly:>10.2f}x")
    print("\n   The multiple is constant below $175 a month, the cap divided by")
    print("   twelve, and falls above it: reaching the annual maximum partway")
    print("   through the year leaves December less to absorb.")

    # ---- what the tool actually tells that person
    print("\n4. SO THE TOOL HAS TO BE ABLE TO SAY NO\n")
    a = advise([60.0] * 12, year, 1)
    print(f"   Asked about $60 a month, it returns: {a.verdict}.")
    print(f"   {a.headline}")

    print("\n" + "=" * 74)
    print("Reproduce every number:   python evals/run.py")
    print("Run the test suite:       python -m pytest tests/ -q")
    print("Your own numbers:         python run.py --costs 60")
    print("=" * 74)
    return 0


def main(argv: list[str] | None = None) -> int:
    _safe_stdout()
    _require_python()
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        import whenyoupay  # noqa: F401
    except ImportError as exc:
        sys.exit(
            f"Could not import the whenyoupay package from {HERE}.\n"
            f"Run this script from inside the cloned repository "
            f"(the folder containing whenyoupay/).\nUnderlying error: {exc}")

    # No arguments means "show me what this is", which is what someone who has
    # just cloned it wants. Anything else is a real query, so hand it to the CLI.
    try:
        if not args:
            return _demo()
        from whenyoupay.cli import main as cli_main
        return cli_main(args)
    except ValueError as exc:
        # Rejected input is a conversation with the user, not a crash. The
        # engine and the rules raise ValueError with a sentence already written
        # for a person; a traceback on top of it just buries the sentence.
        print(f"\nThat input cannot be used: {exc}", file=sys.stderr)
        print("Try:  python run.py --costs 60", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()                       # leave the prompt on its own line
        raise SystemExit(130)
