# WhenYouPay

**The Medicare Prescription Payment Plan changes when you pay, never what you owe. How much it helps is decided by the calendar, not by your need.**

Weekend Builds in Healthcare AI · #9

---

## The programme

Since 2025, any Part D enrollee can ask their plan to spread their out-of-pocket
drug costs across the calendar year instead of paying at the pharmacy counter.
No interest, no fees. In 2026 the annual out-of-pocket ceiling is **$2,100**.

The formula is in [42 CFR 423.137](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.137)
and it is four lines of arithmetic:

- **First month of participation:** (annual threshold − out-of-pocket costs
  already incurred this year) ÷ months remaining
- **Every month after:** (unpaid balance + new out-of-pocket costs) ÷ months
  remaining
- Months remaining **includes** the month being billed
- No interest, no fees, and the total is unchanged

That last clause is the whole story. This repository computes what those four
lines do to a person's year, and tells them plainly when the answer is "do not
join."

## What the arithmetic does

Run `python evals/run.py`. Every figure below comes out of it in under a second.

### 1. Working as intended

An expensive drug starts in January. $1,800 that month, small copays after.

| | worst single month |
|---|---:|
| at the pharmacy counter | **$1,800** |
| in the programme, joined in January | **$223** |

Same $2,075 owed across the year, either way. This is the case the programme was
built for, and it does it well.

### 2. The calendar decides how much protection you get

Now move the drug. Same person, same drug, same $1,800 — and they enrol **in the
month it starts**. Nobody is late, nobody made a mistake.

| drug starts | months left to spread over | worst month | relief |
|---|---:|---:|---:|
| January | 12 | $223 | 88% |
| April | 9 | $265 | 85% |
| July | 6 | $352 | 80% |
| September | 4 | $488 | 73% |
| November | 2 | $925 | 49% |
| December | 1 | $1,800 | **0%** |

A diagnosis in January gets 88% of the shock absorbed. The identical diagnosis in
November gets 49%. In December, nothing at all.

Nobody chooses when they get sick. The formula divides by the months that happen
to be left, so the protection is allocated by the date on the prescription.

### 3. For people whose costs are already level, it backfires

Someone paying a steady $60 a month. Nothing dramatic, no shock, just a chronic
condition and a maintenance drug.

| | January | ... | October | November | **December** |
|---|---:|---|---:|---:|---:|
| at the counter | $60 | | $60 | $60 | **$60** |
| in the programme | $60 | | $91 | $121 | **$181** |

Their December bill is **3.02× what they would have paid at the counter**, and
that multiple is identical at $20 a month, $60 a month, or $150 a month. It is a
property of the formula, not of the person's income. Above $175 a month (the
threshold divided by twelve) it drifts higher still.

Nothing has gone wrong. The balance simply has fewer and fewer months to be
divided into. A programme built to flatten costs manufactures a cliff for the
people whose costs were already flat — which is most people with a chronic
condition and a stable prescription.

**This is why the tool has to be able to say no.** On these numbers it returns
*"Do not join. It would not lower your worst month and it would raise your later
ones."*

### 4. The 72-hour door

If you pay at the counter and *then* hear about the programme, that money is
gone from it. Undoing an already-adjudicated claim is possible only within
**72 hours**, and only where the enrollee believes delay "may seriously
jeopardize their life, health, or ability to regain maximum function"
[42 CFR 423.137(c)].

| $1,800 paid at the counter in January, then you join in… | relief |
|---|---:|
| January (before paying) | $1,577 |
| February | **$0** |
| any later month | **$0** |

The programme is at its most valuable in the month a person is least likely to
have heard of it.

## The invariant

Everything rests on one claim, and it is asserted over every cost shape and
every possible joining month — 96 combinations, largest discrepancy **$0.00**:

> What you pay across the year is identical whether or not you participate.

Anything still owed on 31 December counts toward that total. A balance *can*
survive the year end when someone joins in the last month or two; the regulation
anticipates this and treats it as a plan loss, with the enrollee's coverage not
forfeited [42 CFR 423.137(e)].

The tool is also tested never to use the words *save*, *savings*, *cheaper* or
*discount*. It cannot save anyone money and should never imply it does.

## Try it

```bash
pip install whenyoupay

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
| the shapes | `whenyoupay/profiles.py` | cost patterns that make the programme behave differently |

**No model touches a number anywhere in this repository.** Code computes every
dollar and every date. The only job a language model has here is putting the
result into a sentence a person can act on, and that is the last step, not the
first.

Every claim the tool makes about the rules carries its citation, and a test
asserts that the citations it emits are real entries in `rules.py` rather than
free text.

```bash
python evals/run.py            # every number in this README
python -m pytest tests/ -q     # 24 tests
```

## Limits

**The cost profiles are shapes, not data.** $1,800 in January is a plausible
specialty-drug month, not a measurement of anyone. The programme's behaviour —
the relief curve, the 3.02× December, the zero after the counter — is a property
of the formula and holds for any numbers you put in. The specific dollars are
illustrative and labelled as such.

**Plan-level detail is out of scope.** Real billing involves the plan's own
statement cycle, mid-year formulary changes, drugs moving tiers, and enrollees
switching plans. None of that is modelled. The arithmetic here is the
regulation's, not any plan's implementation of it.

**Extra Help is the bigger lever and this tool does not check it.** The Part D
low-income subsidy reduces what you *owe*, which this programme never does. The
tool says so in every single output, because someone who qualifies for Extra Help
and joins this instead has taken the smaller of two benefits.

**Three things I got wrong, all in the history.** I first asserted the
conservation invariant as `billed == counter`, and it failed by $360 — because a
balance can genuinely still be outstanding on 31 December, which I had not read
carefully enough. I flagged "you will pay more than the counter in later months"
as a warning on every profile, including the ones where it is simply the
mechanism working and the trade is a good one; crying wolf on the helpful cases
would have made the real warnings worthless. And I assumed the 3.02× December
multiple was a universal constant, until testing it above $175 a month showed it
drifts — the first-month cap changes the shape.

## Sources

- **42 CFR 423.137**, Medicare Prescription Payment Plan — the monthly cap
  formula, election timing, the 72-hour retroactive window, the grace period,
  and year-end balances ·
  [eCFR](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.137)
- **Inflation Reduction Act of 2022, sec. 11202**, adding section
  1860D-2(b)(2)(E) to the Social Security Act — the statute behind the programme
- **Part D annual out-of-pocket threshold**: $2,000 (2025), $2,100 (2026) ·
  SSA 1860D-2(b)(4)(B) as amended by IRA sec. 11201, with annual figures
  published by CMS
- **CMS**, Medicare Prescription Payment Plan programme guidance ·
  [cms.gov](https://www.cms.gov/inflation-reduction-act-and-medicare/part-d-improvements/medicare-prescription-payment-plan)

No patient data of any kind is used or present. Every number in this repository
is arithmetic applied to a stated cost shape.

## License

MIT. Personal project — not affiliated with, endorsed by, or representing any
employer. Not advice; if this affects you, your plan, your State Health
Insurance Assistance Program (SHIP), and 1-800-MEDICARE can all help for free.
