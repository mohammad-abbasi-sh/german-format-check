# german-format-check

**Catch English-style formatting inside German text — the deterministic checker agents were missing.**

Agents write German the way they write English, because English is
most of their training data. The mistakes are specific and
repeatable: a price as `€29.99` (German is `29,99 €` — comma
decimal, symbol after the amount), a date as `November 20, 2026`
(German is `20.11.2026`), a time as `2:30 PM` (German is `14:30
Uhr`), a city as `Muenchen`, a month as `January`, a temperature
as `20°C` (DIN 5008 wants `20 °C`). Each one on its own looks like
a typo; together they mark the text as machine-written English in
a German coat — and one of them, the decimal separator, changes
the meaning of a price.

## What it checks

| Code | Rule | Wrong | Right |
|------|------|-------|-------|
| GFC-01 | English decimal point | 29.99 · 1,234.56 | 29,99 · 1.234,56 |
| GFC-02 | English thousands comma | 1,234 · 1,000,000 | 1.234 · 1.000.000 |
| GFC-03 | Currency before amount | €29.99 · EUR 29.99 | 29,99 € |
| GFC-04 | US date | 11/20/2026 · November 20, 2026 | 20.11.2026 |
| GFC-05 | 12-hour time | 2:30 PM · 9:15 AM | 14:30 Uhr · 09:15 Uhr |
| GFC-06 | Percent without space (DIN 5008) | 19% | 19 % |
| GFC-07 | US-style phone | (030) 123-4567 · +49-30-1234567 | 030 1234567 · +49 30 1234567 |
| GFC-08 | Postal code | D-10115 · Berlin, 10115 | 10115 · 10115 Berlin |
| GFC-09 | ASCII umlaut/ß substitutes | Muenchen · Strasse · weiss | München · Straße · weiß |
| GFC-10 | English month names | January · March · October | Januar · März · Oktober |
| GFC-11 | English ordinals | 1st · 2nd · 3rd | 1. · 2. · 3. |
| GFC-12 | Straight double quotes | "Hallo" | „Hallo“ |
| GFC-13 | Missing space before unit | 20°C · 10km · 5kg | 20 °C · 10 km · 5 kg |
| GFC-14 | "VAT" in German text | VAT | USt. |
| GFC-15 | Day number without dot | 20 November 2026 | 20. November 2026 |

Severity: GFC-06, GFC-09, GFC-12 and GFC-14 are **warnings** — they
do not fail the build unless `--strict` is passed. The other eleven
are **errors**.

Formatters: numbers (`1234.56` → `1.234,56`), money (`29.99 EUR`
→ `29,99 €`), dates (`2026-11-20` → `20.11.2026` / `20. November
2026`), phones (`+493012345678` → `+49 30 12345678`).

## Before / after

```text
$ python3 scripts/german_format_check.py check sample-de.txt
GFC-03 [error] (14-20): Currency symbol before the amount: '€29.99' -> '29,99 €'
GFC-04 [error] (44-61): US date: 'November 20, 2026' -> '20.11.2026'
GFC-05 [error] (65-72): 12-hour time: '2:30 PM' -> '14:30 Uhr'
GFC-09 [warning] (76-84): ASCII substitute for umlaut/ß: 'Muenchen' -> 'München'
GFC-09 [warning] (90-97): ASCII substitute for umlaut/ß: 'Strasse' -> 'Straße'
GFC-13 [error] (102-106): Missing space before unit: '10km' -> '10 km'
GFC-06 [warning] (125-126): Percent without a space (DIN 5008): '9%' -> '9 %'
GFC-07 [error] (143-157): US-style phone number: '(030) 123-4567' -> '030 1234567'
5 error(s), 3 warning(s).

$ python3 scripts/german_format_check.py fix sample-de.txt
Der Preis ist 29,99 € und das Treffen ist am 20.11.2026 um 14:30 Uhr in München. Die Straße ist 10 km lang und kostet 19 % mehr. Rufen Sie 030 1234567 an.
```

## Honest framing: what already exists

German i18n help exists — as style guidance, for one framework or
one concern at a time:

- OpenClaw's i18n skill — covers formatting in one table row
  among many languages, with no deterministic checker: it tells
  an agent the rule exists, it does not find the violations in a
  text.
- [cyrus-cai/claude-i18n-style](https://github.com/cyrus-cai/claude-i18n-style)
  — terminology and style guidance, not a formatting audit: no
  CLI, no fixes, no tests.
- [netresearch/german-technical-writing-skill](https://github.com/netresearch/german-technical-writing-skill)
  — technical-writing guidance, not a checker: it improves how
  German docs are written, it does not audit a text for
  English-style numbers, dates and currency.

A GitHub repository search on 2026-11-20 for "german formatting
skill" and "de-DE format checker" returned 0 dedicated
repositories. None of the neighbours above is an agent skill with
a deterministic stdlib checker, an automatic fix, a Cursor rule
and an MCP server. This repo is that layer — it complements the
style guides, it does not replace them.

## Install

**Claude Code / Claude.ai** — copy the skill directory, or upload
the `dist/german-format-check-skill.zip`:

```bash
cp -r skills/german-format-check ~/.claude/skills/
```

**Cursor** — copy `cursor/german-format-check.mdc` into your
project's `.cursor/rules/` (see `cursor/README.md` for Windsurf,
Cline and Continue).

**MCP (any client)** — the stdio server in `mcp-server/` exposes
`check_text`, `fix_text`, `format_number`, `format_money`,
`format_date` and `list_german_format_checks`:

```json
{
  "mcpServers": {
    "german-format-check": {
      "command": "python3",
      "args": ["mcp-server/german_format_check_mcp_server.py"]
    }
  }
}
```

**Direct use** — no install, no dependencies (Python 3.9+ stdlib
only):

```bash
python3 skills/german-format-check/scripts/german_format_check.py check text-de.txt
python3 skills/german-format-check/scripts/german_format_check.py fix text-de.txt
python3 skills/german-format-check/scripts/german_format_check.py format-money 29.99 EUR
```

Exit codes: `0` = clean · `1` = errors found (or warnings, with
`--strict`) · `2` = usage error. `--json` gives machine-readable
output for CI.

## Verification (no statistical claims without a run)

- **180 tests pass** (`pytest tests/` — 170 engine/CLI tests, 10
  MCP stdio tests): every rule code with positive and negative
  vectors, `fix()` round-trips to zero findings on every test
  vector and on both fixtures, the four formatters including edge
  cases (negative numbers, zero, large numbers, `29.99 EUR`,
  long-form `20. November 2026`), CLI exit codes and `--json`
  output, and MCP stdio end-to-end (initialize → tools/list →
  tools/call).
- The demo paragraph (`tests/fixtures/sample-de.txt`) is checked
  at 5 errors + 3 warnings and fixes to a text that re-checks
  clean; the clean fixture (`tests/fixtures/sample-clean-de.txt`)
  exits 0.
- Two bugs were caught by the tests before release, not after:
  the GFC-15 day+month rule missed capitalised English months
  (`20 March 2026`) for a missing `re.IGNORECASE`, and
  `format_money` passed a `Decimal` to a formatter that only
  accepted int/float/str.

## What it does not do

- It does not detect the language of a text. `November` is spelled
  the same in English and German and is never flagged; a whole
  English paragraph inside a German document is a
  language-detection problem, not a formatting one.
- It does not flag ISO dates (`2026-11-20`) — the correct machine
  format, fine in code and in prose that quotes code.
- ASCII substitutes (GFC-09) are warnings because URLs, e-mail
  addresses and code legitimately use them; the checker cannot
  tell prose from a URL.
- The phone formatter guesses the area-code length (2 digits for
  Berlin/Hamburg/Frankfurt/München, 3 for mobiles and most other
  landlines); small-town 4–5 digit area codes need a hand check.
- German-only (de-DE). Swiss German (de-CH: no ß, «...» quotes)
  and Austrian addresses differ — roadmap, not v1.

See `skills/german-format-check/references/formatting-rules.md`
for the reasoning behind each rule, and
`skills/german-format-check/references/examples.md` for worked
before/after cases.

## Roadmap

- Swiss German (de-CH) variant: no ß, «...» quotes, `CHF` handling.
- Austrian addresses and phone formats.
- `.mdc` auto-fix on save (Cursor hook).
- CI action: fail a PR when German copy introduces a GFC error.
- More ASCII-substitute words, gated by a false-positive audit
  (over-eager `oe`→`ö` rewriting is a known trap — see GFC-09).

## License

MIT. Persian version: [README-fa.md](README-fa.md).
