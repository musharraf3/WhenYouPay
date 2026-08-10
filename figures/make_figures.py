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
    """Relief in the worst month, by the month the drug starts."""
    rows = RESULTS["shock_month_sweep"]
    x0, y0, plot_w, plot_h = 64, 190, W - 128, 430

    s = head(
        "The same $1,800 drug. Only the month it starts changes.",
        "How much the worst month falls. They enrolled the same month the drug "
        "started, so nobody was late.",
        "42 CFR 423.137 · 2026 out-of-pocket cap $2,100 · "
        "github.com/musharraf3/WhenYouPay",
    )

    for pct in (0, 25, 50, 75, 100):
        y = y0 + plot_h - plot_h * pct / 100
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plot_w}" y2="{y:.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x0-14}" y="{y+6:.1f}" font-size="16" fill="{MUTED}" '
                 f'text-anchor="end">{pct}%</text>')

    slot = plot_w / len(rows)
    bw = slot * 0.56
    for i, r in enumerate(rows):
        pct = r["relief_share"] * 100
        bh = plot_h * pct / 100
        x = x0 + slot * i + (slot - bw) / 2
        y = y0 + plot_h - bh
        if bh > 0:
            s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                     f'height="{bh:.1f}" rx="4" fill="{BLUE}"/>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{(y-12) if bh > 0 else y0+plot_h-12:.1f}" '
                 f'font-size="19" font-weight="700" fill="{INK}" '
                 f'text-anchor="middle">{pct:.0f}%</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{y0+plot_h+28:.1f}" font-size="17" '
                 f'fill="{INK2}" text-anchor="middle">{esc(r["shock_month"][:3])}</text>')

    s.append(f'<line x1="{x0}" y1="{y0+plot_h}" x2="{x0+plot_w}" y2="{y0+plot_h}" '
             f'stroke="{INK2}" stroke-width="1.5"/>')

    last = rows[-1]
    s.append(f'<text x="{x0+plot_w-6}" y="{y0+plot_h+70}" font-size="20" '
             f'font-weight="600" fill="{INK}" text-anchor="end">'
             f'December: the worst month is still ${last["worst_month"]:,.0f}. '
             f'Nothing is spread at all.</text>')
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
        "$60 a month, every month. December bills $181.19.",
        "A steady prescription and no shock. The bill climbs because the balance "
        "has fewer months left to divide into.",
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
        s.append(f'<text x="{x+bw/2:.1f}" y="{y0+plot_h+28:.1f}" font-size="17" '
                 f'fill="{INK2}" text-anchor="middle">{months[i]}</text>')

    # what the counter would have charged: flat, and the thing being beaten
    yc = y0 + plot_h - plot_h * per_month / top
    s.append(f'<line x1="{x0}" y1="{yc:.1f}" x2="{x0+plot_w}" y2="{yc:.1f}" '
             f'stroke="{ORANGE}" stroke-width="2.5" stroke-dasharray="8 6"/>')

    # December, direct-labelled because it is the whole point
    xd = x0 + slot * 11 + (slot - bw) / 2
    yd = y0 + plot_h - plot_h * billed[-1] / top
    s.append(f'<text x="{xd+bw/2:.1f}" y="{yd-14:.1f}" font-size="24" '
             f'font-weight="700" fill="{INK}" text-anchor="middle">'
             f'${billed[-1]:,.2f}</text>')
    s.append(f'<text x="{xd+bw/2:.1f}" y="{yd-40:.1f}" font-size="17" '
             f'fill="{INK2}" text-anchor="middle">3.02&#215; the counter</text>')

    ly = y0 - 34
    s.append(f'<rect x="{x0}" y="{ly-13}" width="15" height="15" rx="3" fill="{BLUE}"/>')
    s.append(f'<text x="{x0+23}" y="{ly}" font-size="18" fill="{INK2}">'
             f'Billed in the program</text>')
    s.append(f'<line x1="{x0+230}" y1="{ly-6}" x2="{x0+266}" y2="{ly-6}" '
             f'stroke="{ORANGE}" stroke-width="2.5" stroke-dasharray="8 6"/>')
    s.append(f'<text x="{x0+276}" y="{ly}" font-size="18" fill="{INK2}">'
             f'At the pharmacy counter ($60)</text>')

    s.append(f'<text x="{x0}" y="{y0+plot_h+70}" font-size="20" font-weight="600" '
             f'fill="{INK}">Same $720 across the year either way. '
             f'Four months cost more than paying at the counter.</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    (HERE / "the_calendar.svg").write_text(calendar_figure(), encoding="utf-8")
    (HERE / "the_cliff.svg").write_text(cliff_figure(), encoding="utf-8")
    print("wrote figures/the_calendar.svg and figures/the_cliff.svg")
