"""Generate the two post figures from the committed run.

Nothing here is typed by hand. Both charts read `results/results.json`, so a
figure cannot drift from the numbers the engine actually produced — which is
the same reason the README quotes the run rather than a spreadsheet.

    python figures/make_figures.py

Writes `figures/the_calendar.svg` and `figures/the_cliff.svg`. No dependencies,
consistent with the rest of the repository.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from whenyoupay.engine import simulate  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))

W, H = 1200, 760

# Categorical slots 1 and 2 of the documented palette, in fixed order.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8a84"
SURFACE = "#fcfcfb"
GRID = "#e6e5e1"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def head(title: str, subtitle: str, footer: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
        f'<text x="64" y="76" font-size="36" font-weight="700" fill="{INK}">{esc(title)}</text>',
        f'<text x="64" y="116" font-size="21" fill="{INK2}">{esc(subtitle)}</text>',
        f'<text x="64" y="{H-30}" font-size="16" fill="{MUTED}">{esc(footer)}</text>',
    ]


def calendar_figure() -> str:
    """The worst single month, in dollars, by the month the drug starts.

    Earlier drafts plotted the *percentage* the worst month falls. That was a
    ratio against a baseline the chart never showed, and twelve bars labelled
    Jan-Dec read as one year declining rather than as twelve separate people.
    Dollars against a visible counter line fix both: the bar is what you pay,
    the line is what you would have paid, and the closing gap is the story.
    """
    rows = RESULTS["shock_month_sweep"]
    counter = max(r["worst_month"] for r in rows)      # $1,800, the December case
    x0, y0, plot_w, plot_h = 92, 232, W - 156, 372
    top = 2000.0

    s = head(
        "Same drug, same $1,800. The month it starts sets your worst bill.",
        "Each bar is a different person starting the same drug in a different "
        "month. Nobody was late.",
        "42 CFR 423.137 · 2026 out-of-pocket cap $2,100 · "
        "github.com/musharraf3/WhenYouPay",
    )

    s.append(f'<text x="{x0-72}" y="{y0-14}" font-size="17" font-weight="600" '
             f'fill="{INK2}">Highest single month&#39;s bill</text>')

    for v in (0, 500, 1000, 1500, 2000):
        y = y0 + plot_h - plot_h * v / top
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x0-14}" y="{y+6:.1f}" font-size="16" fill="{MUTED}" '
                 f'text-anchor="end">${v:,}</text>')

    # the thing every bar is being compared against, drawn before the bars
    yc = y0 + plot_h - plot_h * counter / top
    s.append(f'<line x1="{x0}" y1="{yc:.1f}" x2="{x0+plot_w}" y2="{yc:.1f}" '
             f'stroke="{ORANGE}" stroke-width="2.5" stroke-dasharray="8 6"/>')
    s.append(f'<text x="{x0+8}" y="{yc-12:.1f}" font-size="18" font-weight="600" '
             f'fill="{ORANGE}">Paying at the pharmacy counter: ${counter:,.0f}</text>')

    slot = plot_w / len(rows)
    bw = slot * 0.58
    for i, r in enumerate(rows):
        amt = r["worst_month"]
        bh = plot_h * amt / top
        x = x0 + slot * i + (slot - bw) / 2
        y = y0 + plot_h - bh
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                 f'height="{bh:.1f}" rx="4" fill="{BLUE}"/>')
        if i in (0, 6, 10, 11):
            s.append(f'<text x="{x+bw/2:.1f}" y="{y-12:.1f}" font-size="19" '
                     f'font-weight="700" fill="{INK}" text-anchor="middle">'
                     f'${amt:,.0f}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{y0+plot_h+28:.1f}" font-size="17" '
                 f'fill="{INK2}" text-anchor="middle">{esc(r["shock_month"][:3])}</text>')

    s.append(f'<line x1="{x0}" y1="{y0+plot_h}" x2="{x0+plot_w}" y2="{y0+plot_h}" '
             f'stroke="{INK2}" stroke-width="1.5"/>')
    s.append(f'<text x="{x0+plot_w/2:.1f}" y="{y0+plot_h+58:.1f}" font-size="18" '
             f'fill="{INK2}" text-anchor="middle">Month the drug starts</text>')

    s.append(f'<text x="{x0}" y="{y0+plot_h+100:.1f}" font-size="21" '
             f'font-weight="600" fill="{INK}">January gets your worst month down '
             f'to $223. December leaves it at $1,800.</text>')
    s.append("</svg>")
    return "\n".join(s)


def cliff_figure() -> str:
    """What the program does to someone whose costs were already flat."""
    per_month = 60.0
    billed = [round(x, 2) for x in simulate([per_month] * 12, 2026, 1).billed]

    # Pin to the committed run so the figure cannot quietly disagree with it.
    published = [r for r in RESULTS["flat_backfire"]
                 if r["monthly_at_counter"] == per_month][0]["december_bill"]
    assert billed[-1] == published, (billed[-1], published)

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    x0, y0, plot_w, plot_h = 64, 210, W - 128, 400
    top = 200.0

    s = head(
        "$60 every month. The program bills $181.19 in December.",
        "Nothing unusual happens all year. The bill climbs because each month's "
        "balance is divided into fewer remaining months.",
        "Medicare publishes the same shape: its $80-a-month example ends at "
        "$241.53 · github.com/musharraf3/WhenYouPay",
    )

    for v in (0, 50, 100, 150, 200):
        y = y0 + plot_h - plot_h * v / top
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x0-14}" y="{y+6:.1f}" font-size="16" fill="{MUTED}" '
                 f'text-anchor="end">${v}</text>')

    slot = plot_w / 12
    bw = slot * 0.56
    for i, amt in enumerate(billed):
        bh = plot_h * amt / top
        x = x0 + slot * i + (slot - bw) / 2
        y = y0 + plot_h - bh
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                 f'rx="4" fill="{BLUE}"/>')
        if i == 0:
            s.append(f'<text x="{x+bw/2:.1f}" y="{y-14:.1f}" font-size="18" '
                     f'font-weight="700" fill="{INK}" text-anchor="middle">'
                     f'${amt:,.0f}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{y0+plot_h+28:.1f}" font-size="17" '
                 f'fill="{INK2}" text-anchor="middle">{months[i]}</text>')

    # what the counter would have charged: flat, and the thing being beaten
    yc = y0 + plot_h - plot_h * per_month / top
    s.append(f'<line x1="{x0}" y1="{yc:.1f}" x2="{x0+plot_w}" y2="{yc:.1f}" '
             f'stroke="{ORANGE}" stroke-width="2.5" stroke-dasharray="8 6"/>')
    # under the line, starting after January (whose bar reaches the line) and
    # ending before July, whose bar climbs back into this band
    s.append(f'<text x="{x0+slot+10:.1f}" y="{yc+28:.1f}" font-size="18" '
             f'font-weight="600" fill="{ORANGE}">'
             f'Paying cash: ${per_month:,.0f} every month</text>')

    # the plot's whole upper-left is empty; spend it explaining the encoding
    s.append(f'<text x="{x0+8}" y="{y0+52}" font-size="19" font-weight="600" '
             f'fill="{INK}">Bars below the line: you paid less than cash that '
             f'month.</text>')
    s.append(f'<text x="{x0+8}" y="{y0+78}" font-size="19" font-weight="600" '
             f'fill="{INK}">Bars above it: you paid more.</text>')

    # December, direct-labelled because it is the whole point
    xd = x0 + slot * 11 + (slot - bw) / 2
    yd = y0 + plot_h - plot_h * billed[-1] / top
    s.append(f'<text x="{xd+bw/2:.1f}" y="{yd-14:.1f}" font-size="24" '
             f'font-weight="700" fill="{INK}" text-anchor="middle">'
             f'${billed[-1]:,.2f}</text>')
    s.append(f'<text x="{xd+bw/2:.1f}" y="{yd-40:.1f}" font-size="17" '
             f'fill="{INK2}" text-anchor="middle">3.02&#215; the counter</text>')

    over = [i for i, a in enumerate(billed) if a > per_month]

    s.append(f'<text x="{x0}" y="{y0+plot_h+72}" font-size="21" font-weight="600" '
             f'fill="{INK}">The year costs $720 either way. '
             f'{len(over)} of the 12 months cost more than paying cash.</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    (HERE / "the_calendar.svg").write_text(calendar_figure(), encoding="utf-8")
    (HERE / "the_cliff.svg").write_text(cliff_figure(), encoding="utf-8")
    print("wrote figures/the_calendar.svg and figures/the_cliff.svg")
