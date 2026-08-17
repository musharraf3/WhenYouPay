# WhenYouPay

[![ci](https://github.com/musharraf3/WhenYouPay/actions/workflows/ci.yml/badge.svg)](https://github.com/musharraf3/WhenYouPay/actions/workflows/ci.yml)

**The Medicare Prescription Payment Plan changes when you pay, never what you owe. How much it helps is decided by the calendar, not by your need.**

Weekend Builds in Healthcare AI · #9

---

## The program

Since 1 January 2025, any Part D enrollee can ask their plan to spread their
out-of-pocket drug costs across the calendar year instead of paying at the
pharmacy counter. No interest, no fees. In 2026 the annual out-of-pocket
ceiling is **$2,100**.

The 2025 program year ran under CMS program guidance; the codified rule at
42 CFR 423.137 applies to plan years beginning on or after 1 January 2026
(§423.137(a)). Every figure in this repository is a 2026 figure, so the
regulation is the right source for all of them.

The formula is in [42 CFR 423.137](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.137)
and it is two formulas and two guarantees:

- **First month of participation:** (annual threshold − out-of-pocket costs
  already incurred this year) ÷ months remaining — §423.137(c)(1)(i)
- **Every month after:** (unpaid balance + new out-of-pocket costs) ÷ months
  remaining — §423.137(c)(1)(ii)
- Months remaining **includes** the month being billed — §423.137(c)(3)
- The amount billed for a month can never exceed that month's cap —
  §423.137(g)(1)(ii)
- No late fees, interest, or other fees may be charged — §423.137(g)(1)(iii)

Those last two clauses are the whole story. This repository computes what the
formula does to a person's year, and tells them plainly when the answer is "do not
join."

## What the arithmetic does

Run `python evals/run.py`. Every figure below comes out of it in under a second.

### 1. Working as intended

An expensive drug starts in January. $1,800 that month, small copays after.

| | worst single month |
|---|---:|
| at the pharmacy counter | **$1,800** |
| in the program, joined in January | **$223** |

Same $2,075 owed across the year, either way. This is the case the program was
built for, and it does it well.

### 2. The calendar decides how much protection you get

Now move the drug. Same person, same drug, same $1,800 — and they enroll **in the
month it starts**. Nobody is late, nobody made a mistake.

| drug starts | months left to spread over | worst month | relief |
|---|---:|---:|---:|
| January | 12 | $223 | 88% |
| April | 9 | $265 | 85% |
| July | 6 | $352 | 80% |
| September | 4 | $488 | 73% |
| November | 2 | $925 | 49% |
| December | 1 | $1,800 | **0%** |

A diagnosis in January cuts the worst month by 88%. The identical diagnosis in
November cuts it by 49%. In December, not at all. Nothing is forgiven in any of
these rows — the same total is owed either way; only the shape of the year
changes.

Nobody chooses when they get sick. The formula divides by the months that happen
to be left, so the protection is allocated by the date on the prescription.

### 3. For people whose costs are already level, it backfires

Someone paying a steady $60 a month. Nothing dramatic, no shock, just a chronic
condition and a maintenance drug.

| | January | ... | October | November | **December** |
|---|---:|---|---:|---:|---:|
| at the counter | $60 | | $60 | $60 | **$60** |
| in the program | $60 | | $91 | $121 | **$181** |

Their December bill is **3.02× what they would have paid at the counter**, and
that multiple is identical at $20 a month, $60 a month, or $150 a month. It is a
property of the formula, not of the person's income.

Above $175 a month — the threshold divided by twelve — the multiple *falls*,
and steeply: 1.78× at $200 a month, 0.39× at $500. Spending more than
threshold/12 means reaching the annual maximum partway through the year and
paying nothing after it, so December has less left to absorb. The worst case is
not the biggest spender. It is whoever spends almost exactly $175 a month, the
only amount that stays flat all year *and* reaches the ceiling on the last day
of it.

**This is not my finding.** Medicare publishes the same case: a steady $80 a
month through 2026, ending with a December bill of **$241.53** — 3.019× the
monthly cost. It is [example 2 on medicare.gov](https://www.medicare.gov/prescription-payment-plan/examples).
What this repository adds is the observation that the multiple is a constant,
and a tool that tells the person concerned.

Nothing has gone wrong. The balance simply has fewer and fewer months to be
divided into. A program built to flatten costs manufactures a cliff for the
people whose costs were already flat — which is most people with a chronic
condition and a stable prescription.

**This is why the tool has to be able to say no.** On these numbers it returns
*"Do not join. It would not lower your worst month and it would raise your later
ones."*

### 4. The 72-hour door

If you pay at the counter and *then* hear about the program, that money is
gone from it. Undoing an already-adjudicated claim is possible only within
**72 hours**, and only where the enrollee believes delay "may seriously
jeopardize their life, health, or ability to regain maximum function"
[42 CFR 423.137(d)(6)].

| $1,800 paid at the counter in January, then you join in… | relief |
|---|---:|
| January (before paying) | $1,577 |
| February | **$0** |
| any later month | **$0** |

The program is at its most valuable in the month a person is least likely to
have heard of it.

## Checked against Medicare's own examples

Internal consistency cannot catch a misreading of the regulation. Only someone
else's numbers can. Medicare publishes three worked examples for 2026, and
`tests/test_against_medicare_examples.py` runs the engine against all of them.

| example | shape | result |
|---|---|---|
| 1 | $525/month Jan–Apr, hits the ceiling in April | matches; annual total **exactly $2,100.00** |
| 2 | steady $80/month all year | matches; annual total **exactly $960.00** |
| 3 | $4/month, $617 in April when participation starts | **exact to the cent, all twelve months** |

Examples 1 and 2 differ from the published tables by 1–6 cents in the closing
months. Medicare's stated annual totals are correct ($2,100 and $960.00); it is
the twelve *printed monthly figures* that add up to $2,100.02 and $959.94, while
this engine's twelve add to the stated total exactly. The difference is rounding
presentation in a consumer-facing table, not an error in the program or in the
method.

Example 1 also settles the assumption everything else rests on. Its first month
is **$175.00 = $2,100 ÷ 12**, which is only true if "months remaining" includes
the month being billed, exactly as §423.137(c)(3) says.

Rounding is half-up, not banker's: Medicare bills $58.925 as $58.93 and $94.925
as $94.93. Banker's rounding gives $58.92 and $94.92 and the year drifts.

## The invariant

Everything rests on one claim, and it is asserted over every cost shape and
every possible joining month — 96 combinations, largest discrepancy **$0.00**:

> What you pay across the year is identical whether or not you participate.

Anything still owed on 31 December counts toward that total, though in this
model nothing ever is: December divides by one remaining month, so whatever is
left gets billed in full. An earlier version of this README claimed a balance
could survive the year end, and a test asserted it — both were artifacts of the
ceiling bug described below.

42 CFR 423.137(g)(4) is still cited and still real. It governs unsettled
balances, which arise from non-*payment*; this engine models what a plan bills,
not what an enrollee has paid, so it cannot produce one.

The tool is also tested never to use the words *save*, *savings*, *cheaper* or
*discount*. It cannot save anyone money and should never imply it does.

## Try it

```bash
git clone https://github.com/musharraf3/WhenYouPay && cd WhenYouPay
pip install -e .

whenyoupay --costs "1800 25 25 25 25 25 25 25 25 25 25 25" --join 1
whenyoupay --costs 60 --join 1          # one number means every month
whenyoupay --profile november_shock --join 11
whenyoupay --costs 60 --join 1 --json
```

No network, no API key, no dependencies.

## How it is built

| layer | file | what it does |
|---|---|---|
| the regulation | `whenyoupay/rules.py` | every constant and rule, each carrying its citation |
| the arithmetic | `whenyoupay/engine.py` | month-by-month simulation, deterministic |
| the judgement | `whenyoupay/advise.py` | what to tell the person, including when to tell them not to bother |
| the shapes | `whenyoupay/profiles.py` | cost patterns that make the program behave differently |

**No model touches a number anywhere in this repository.** Code computes every
dollar and every date. The only job a language model has here is putting the
result into a sentence a person can act on, and that is the last step, not the
first.

Every claim the tool makes about the rules carries its citation, and a test
asserts that the citations it emits are real entries in `rules.py` rather than
free text.

```bash
python evals/run.py            # every number in this README
python -m pytest tests/ -q     # 37 tests
```

## Limits

**The cost profiles are shapes, not data.** $1,800 in January is a plausible
specialty-drug month, not a measurement of anyone. The program's behavior —
the relief curve, the 3.02× December, the zero after the counter — is a property
of the formula and holds for any numbers you put in. The specific dollars are
illustrative and labeled as such.

**Plan-level detail is out of scope.** Real billing involves the plan's own
statement cycle, mid-year formulary changes, drugs moving tiers, and enrollees
switching plans. None of that is modeled. The arithmetic here is the
regulation's, not any plan's implementation of it.

**Extra Help is the bigger lever and this tool does not check it.** The Part D
low-income subsidy reduces what you *owe*, which this program never does. The
tool says so in every single output, because someone who qualifies for Extra Help
and joins this instead has taken the smaller of two benefits.

**The engine ignored the annual out-of-pocket maximum, and the fixtures hid
it.** `simulate()` took the monthly costs it was given at face value, so asking
it about $500 a month returned $6,000 for a year that costs $2,100 — while the
advice printed beside that number said *"above the ceiling you pay nothing more
for covered Part D drugs."* The tool stated the rule and contradicted it in the
same breath.

It survived because every fixture applied the cap by hand. Medicare's own
Example 1 is `[525, 525, 525, 525, 0, 0, 0, 0, 0, 0, 0, 0]` — a human did the
capping and typed the zeros, and the engine never had to. All three published
examples reconciled to the cent while the arithmetic underneath was wrong for
anyone outside them.

That is the uncomfortable one, because this project's whole argument is that
external validation catches what internal consistency cannot. Here it did not.
The published examples all sat inside the blind spot. What eventually caught it
was asking the engine a question no fixture asked: what happens above the
ceiling. Fixed in `simulate()`, with three tests that would have caught it and a
conservation sweep that now includes profiles running past the threshold.

**Five things I got wrong before that, all in the history.** I first asserted the
conservation invariant as `billed == counter`, and it failed by $360 — because a
balance can genuinely still be outstanding on 31 December, which I had not read
carefully enough. I flagged "you will pay more than the counter in later months"
as a warning on every profile, including the ones where it is simply the
mechanism working and the trade is a good one; crying wolf on the helpful cases
would have made the real warnings worthless. I assumed the 3.02× December
multiple was a universal constant, until testing above $175 a month showed it
does not hold there — though for two versions I had the direction wrong, and the
reason is the next confession. **I cited the formula to the wrong paragraphs** — (d)(2)(i) and (d)(2)(ii)
rather than (c)(1)(i) and (c)(1)(ii) — which is the kind of error that discredits
everything around it, and it survived until I went back to the regulation to
check. And I used full floating-point precision for carried balances, which is
defensible arithmetic and wrong billing: the balance that rolls forward is the
rounded one, and using the exact one put the engine a few cents away from
Medicare's published examples.

## Sources

- **42 CFR 423.137**, Medicare Prescription Payment Plan ·
  [eCFR](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.137)
  — monthly cap formula at (c)(1); months-remaining definition at (c)(3);
  election and processing at (d)(1)–(4); retroactive election at (d)(6); grace
  period at (f)(2)(ii) and (f)(3); year-end balances at (g)(4)
- **Medicare.gov**, worked examples of the payment option — the validation set ·
  [medicare.gov](https://www.medicare.gov/prescription-payment-plan/examples)
- **CMS**, Medicare Prescription Payment Plan final part one guidance — confirms
  a participant is billed the lesser of actual costs and the cap, that costs
  incurred before election are excluded, and that plans may not charge fees
- **Inflation Reduction Act of 2022, sec. 11202**, adding section
  1860D-2(b)(2)(E) to the Social Security Act — the statute behind the program
- **Part D annual out-of-pocket threshold**: $2,000 (2025), $2,100 (2026) ·
  SSA 1860D-2(b)(4)(B) as amended by IRA sec. 11201, with annual figures
  published by CMS
- **CMS**, Medicare Prescription Payment Plan program guidance ·
  [cms.gov](https://www.cms.gov/inflation-reduction-act-and-medicare/part-d-improvements/medicare-prescription-payment-plan)

No patient data of any kind is used or present. Every number in this repository
is arithmetic applied to a stated cost shape.

## License

MIT. Personal project — not affiliated with, endorsed by, or representing any
employer. Not advice; if this affects you, your plan, your State Health
Insurance Assistance Program (SHIP), and 1-800-MEDICARE can all help for free.
