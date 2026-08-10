"""Cost profiles.

These are not data. They are shapes a year of drug spending can take, each
one chosen because it makes the programme behave differently. Numbers are
illustrative and stated as such; nothing here claims to describe any real
person or any real drug price.
"""

from __future__ import annotations

FLAT_LOW = [60.0] * 12
FLAT_MID = [150.0] * 12

JANUARY_SHOCK = [1800.0] + [25.0] * 11
SEPTEMBER_SHOCK = [25.0] * 8 + [1800.0] + [25.0] * 3
NOVEMBER_SHOCK = [25.0] * 10 + [1800.0, 25.0]

TWO_SHOCKS = [900.0] + [25.0] * 5 + [900.0] + [25.0] * 5
RAMPING = [round(40 + 30 * i, 2) for i in range(12)]
CAPPED_EARLY = [1200.0, 900.0] + [0.0] * 10   # hits the ceiling in February

PROFILES = {
    "flat_low": (FLAT_LOW, "steady small copays all year"),
    "flat_mid": (FLAT_MID, "steady moderate copays all year"),
    "january_shock": (JANUARY_SHOCK, "one expensive drug started in January"),
    "september_shock": (SEPTEMBER_SHOCK, "the same drug started in September"),
    "november_shock": (NOVEMBER_SHOCK, "the same drug started in November"),
    "two_shocks": (TWO_SHOCKS, "two costly months, January and July"),
    "ramping": (RAMPING, "costs rising through the year"),
    "capped_early": (CAPPED_EARLY, "reaches the annual ceiling by February"),
}
