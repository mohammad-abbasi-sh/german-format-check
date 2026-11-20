---
name: german-format-check
description: Catch English-style formatting inside German text — English decimals (29.99 instead of 29,99), US dates (11/20/2026 instead of 20.11.2026), 12-hour times (2:30 PM instead of 14:30 Uhr), currency before the amount (EUR 29.99 instead of 29,99 €), ASCII substitutes for umlauts (Muenchen instead of München), English month names (January instead of Januar), straight quotes, missing spaces before units (20°C), and 8 more rules (GFC-01..GFC-15), each with an automatic fix, plus German formatters for numbers, money, dates and phones. Use when an agent writes, translates, edits or reviews German text — a blog post, an email, a product description, a form, a contract draft, UI strings — or before publishing anything in German. Also use before sending German text to a client or a printer: a wrong decimal separator changes a price.
---

# German format check — stop shipping German text formatted like English

Agents write German the way they write English, because English is
most of their training data. The mistakes are specific and
repeatable: a price written as `€29.99` (German is `29,99 €` — comma
decimal, symbol after the amount), a date as `November 20, 2026`
(German is `20.11.2026`), a time as `2:30 PM` (German is `14:30
Uhr`), a city as `Muenchen`, a month as `January`, a temperature as
`20°C` (DIN 5008 wants `20 °C`). Each one on its own looks like a
typo; together they mark the text as machine-written English in a
German coat — and one of them, the decimal separator, changes the
meaning of a price.

This skill is the deterministic check for all of it: one
zero-dependency stdlib tool, 15 rules (GFC-01..GFC-15), an automatic
fix for every rule, and formatters for numbers, money, dates and
phones. It complements the i18n and style skills that already
exist — OpenClaw's i18n skill covers formatting in one table row
among many languages with no checker, cyrus-cai/claude-i18n-style
is about terminology and style, and netresearch's
german-technical-writing-skill is about technical writing. None of
them is a deterministic audit that finds and fixes the errors in a
German text. This repo is that layer.

## The contract

1. **Check first, with the tool — never eyeball it.** Run the
   bundled checker (zero-dependency, Python stdlib only):

   ```bash
   python3 scripts/german_format_check.py check text-de.txt
   python3 scripts/german_format_check.py check --json - < text-de.txt
   echo "Der Preis ist 29.99 Euro." | python3 scripts/german_format_check.py check -
   ```

   Exit codes: `0` = clean · `1` = errors found (or warnings, with
   `--strict`) · `2` = usage error. `--json` gives machine-readable
   output for CI. Each finding names its rule code, its position
   and its suggested fix.

2. **Fix with the tool, then re-check.** Never hand-edit a fix the
   tool can make — hand edits introduce new errors (a fixed
   decimal inside a currency amount, a month name inside a date):

   ```bash
   python3 scripts/german_format_check.py fix text-de.txt > text-de.fixed.txt
   python3 scripts/german_format_check.py check text-de.fixed.txt
   ```

   `fix` applies the fixes and re-checks internally until the text
   is clean, so composite cases (a currency amount that also has
   an English decimal, a date that also has an English month) come
   out right. Do not report a text as fixed after editing it —
   re-run `check` until it exits 0 and quote the final `OK` line.

3. **Format new values with the formatters, never by hand.**

   ```bash
   python3 scripts/german_format_check.py format-number 1234.56   # 1.234,56
   python3 scripts/german_format_check.py format-money 29.99 EUR  # 29,99 €
   python3 scripts/german_format_check.py format-date 2026-11-20   # 20.11.2026
   python3 scripts/german_format_check.py format-date 2026-11-20 --long  # 20. November 2026
   python3 scripts/german_format_check.py format-phone +493012345678  # +49 30 12345678
   ```

   A hand-formatted number is how `1,234.56` slips into a German
   invoice. Use the formatter and the number is right by
   construction.

## The 15 rules

| Code | Rule | Wrong | Right |
|------|------|-------|-------|
| GFC-01 | English decimal point | 29.99 · 3.14 · 1,234.56 | 29,99 · 3,14 · 1.234,56 |
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
are **errors**. See `references/formatting-rules.md` for the
reasoning behind each rule and `references/examples.md` for worked
before/after cases.

## Workflow

```text
write German text -> check -> fix -> check again (exit 0) -> publish
```

Put `check` in CI for any repository that ships German copy: a
failing build on GFC-01..GFC-05, GFC-07, GFC-08, GFC-10, GFC-11,
GFC-13 and GFC-15 catches the errors that change meaning or look
unprofessional, while the warnings (GFC-06, GFC-09, GFC-12,
GFC-14) stay advisory unless `--strict` is set.

## MCP server

`mcp-server/german_format_check_mcp_server.py` exposes the same
capability over stdio JSON-RPC: `check_text`, `fix_text`,
`format_number`, `format_money`, `format_date` and
`list_german_format_checks`. See `tests/test_mcp_server.py` for a
full lifecycle test.

## Limits — say them in every report

- **ISO dates in code are fine.** `2026-11-20` is never flagged:
  it is the correct machine format, and German prose that quotes
  it (a filename, an API field, a log line) should keep it.
- **ASCII substitutes are warnings, not errors.** `Muenchen` in a
  URL, an e-mail address, a username or source code is correct —
  those contexts cannot carry umlauts. Only fix them in prose.
  The checker cannot tell prose from a URL, so it warns and lets
  the human decide.
- **The quotes fix needs paired quotes.** A lone `"` (an inch
  mark, a truncated quote) is left alone — pairing it would guess.
- **November, December, August, September and April are spelled
  the same in English and German** and are never flagged. If the
  surrounding text is English, that is a language-detection
  problem, not a formatting one — this tool does not detect the
  language of a text.
- **The phone formatter guesses the area-code length** (2 digits
  for Berlin/Hamburg/Frankfurt/München, 3 for mobiles and most
  other landlines). Small-town area codes with 4–5 digits are
  formatted with the first 3 digits as the area code — check those
  by hand.
- **The checker is German-only (de-DE).** Swiss German (de-CH)
  differs — no ß, different quotes («...») — and Austrian
  addresses have their own conventions. Both are on the roadmap,
  not in v1.
