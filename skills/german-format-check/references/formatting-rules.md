# Formatting rules — why each GFC rule exists

Every rule below states the German convention, the English habit
that replaces it, and the edge the checker deliberately leaves
alone. The checker is deterministic: it finds patterns, not
intent. When a pattern is ambiguous, the rule says which side it
falls on and why.

## GFC-01 English decimal point (error)

German uses a comma as the decimal separator and a dot for
thousands: `29,99`, `1.234,56`. English does the opposite:
`29.99`, `1,234.56`. A German reader parses `29.99` as two numbers
or as a typo; a price of `29.99` in a German invoice is wrong, not
informal.

Edge cases the checker handles: `1.234,56` (already German) is
never flagged; `20.11.2026` (a German date) is never flagged; a
bare `1.234` (German thousands, three digits after the dot) is
never flagged — an English decimal with three fractional digits
is rare, a German thousands group is common, so the ambiguity is
resolved in favour of German. `2.0.1` (a version number) is never
flagged.

## GFC-02 English thousands comma (error)

`1,234` in German is either a decimal comma followed by a
three-digit fraction (`1,234` = 1.234) or an English thousands
separator. In running German text it is the latter often enough
that the checker flags it and fixes it to `1.234`. `1,234.56`
belongs to GFC-01 (the decimal point claims the whole number) and
is reported once, not twice.

## GFC-03 currency before the amount (error)

DIN 5008 puts the currency symbol after the amount with a space:
`29,99 €`. English puts it before: `€29.99`, `$19.99`, `EUR
29.99`. The fix moves the symbol and repairs the decimal inside
the amount in the same step, so `€29.99` becomes `29,99 €` in one
finding — GFC-01 does not also fire on the same span. A bare
`€29` (no decimal, no thousands) is not flagged: there is no
formatting error in it beyond the symbol position, and moving the
symbol of an integer amount is a style call the checker leaves to
the human. (CHF keeps its code: `29,99 CHF`, since CHF has no
symbol in German use.)

## GFC-04 US date (error)

`11/20/2026`, `2026/11/20`, `November 20, 2026`, `Nov 20, 2026`
all become `20.11.2026`. The slash order is the danger: `11/20`
can only be month/day in the US format, and a German reader who
parses it as day/month gets the 11th of an impossible 20th month.
The month-name form is claimed whole by GFC-04, so `March 5,
2026` is one GFC-04 finding, not GFC-04 plus GFC-10.

Not flagged: ISO `2026-11-20` (the correct machine format, fine
in code and in prose that quotes code) and German `20.11.2026`.

## GFC-05 12-hour time (error)

German uses the 24-hour clock with `Uhr`: `14:30 Uhr`. `2:30 PM`,
`2:30pm`, `9:15 AM` become `14:30 Uhr`, `09:15 Uhr`. 12 AM is
`00:00 Uhr`, 12 PM is `12:30 Uhr` — the noon/midnight edge is the
one humans get wrong, so the checker converts it explicitly.
`14:30` without `Uhr` is not flagged: it is already 24-hour.

## GFC-06 percent without a space (warning, DIN 5008)

`19%` becomes `19 %`. DIN 5008 prescribes the space; Duden
tolerates the closed form in running text, which is why this is a
warning, not an error — it never fails a build unless `--strict`
is passed.

## GFC-07 US-style phone (error)

`(030) 123-4567` and `+49-30-1234567` become `030 1234567` and
`+49 30 1234567`. German numbers group with spaces; hyphens
between the blocks and parentheses around the area code are the
US habit. Note that `(030) 1234567` without a hyphen is *not*
flagged: parentheses around the area code alone are traditional
German style, and the checker does not police style that is
correct.

## GFC-08 postal code (error)

Two cases. `D-10115` drops the `D-` prefix: it has been obsolete
since the 1993 postal reform, and it survives only in old
letterheads and in text copied from them. `Berlin, 10115` becomes
`10115 Berlin`: the German address order puts the postal code
before the city. The city pattern matches a single capitalised
word; a two-word city (`Bad Reichenhall, 83435`) is not caught —
that is a documented gap, not a false positive to chase.

## GFC-09 ASCII substitutes for umlaut/ß (warning)

`Strasse` → `Straße`, `Muenchen` → `München`, `Koeln` → `Köln`,
`weiss` → `weiß`, `gross` → `groß`, `Fuss` → `Fuß`, `Gruss` →
`Gruß`, `Maedchen` → `Mädchen`. The mapping is word-boundary and
case-aware (`Muenchen` → `München`, `WEISS` → `WEIẞ` with the
capital sharp-s). This is a warning, not an error, because ASCII
contexts exist: URLs, e-mail addresses, usernames and source code
legitimately use `Muenchen`. The checker cannot tell prose from a
URL, so it warns and lets the human decide. Only the eight listed
words are mapped — `schoen` is not, because over-eager `oe`→`ö`
rewriting produces false positives (`Poet` is not `Pöt`).

## GFC-10 English month names (error)

`January` → `Januar`, `February` → `Februar`, `March` → `März`,
`May` → `Mai`, `June` → `Juni`, `July` → `Juli`, `October` →
`Oktober`. `November`, `December`, `August`, `September` and
`April` are spelled the same in both languages and are never
flagged — flagging them would be a false positive on correct
German. A month name inside a US date (`March 5, 2026`) is
claimed by GFC-04; a month name after a bare day number (`20
March 2026`) is claimed by GFC-15.

## GFC-11 English ordinals (error)

`1st`, `2nd`, `3rd`, `4th` become `1.`, `2.`, `3.`, `4.` — the
German ordinal is the number followed by a dot. `1.` in correct
German text is never flagged.

## GFC-12 straight double quotes (warning)

`"Hallo"` becomes `„Hallo“` — the German opening quote sits low,
the closing quote sits high. The fix only converts *paired*
quotes: a lone `"` (an inch mark, a truncated quote) is left
alone, because pairing it would be a guess. This is a warning
because straight quotes are also correct in code, in JSON and in
some corporate styles — in prose they are wrong, in code they are
not, and the checker does not know which it is looking at.

## GFC-13 missing space before unit (error)

`20°C` → `20 °C`, `10km` → `10 km`, `5kg` → `5 kg`, `3m` → `3 m`.
DIN 5008 puts a space between the number and the unit (the degree
sign included: `20 °C`, not `20° C`). Covered units: °C, km, kg,
g, mg, m, cm, mm, l, ml. The pattern requires the unit directly
after the digits, so `10 km` is never flagged, and `15min` is
never flagged (the `m` is followed by `in`, not a word boundary).

## GFC-14 "VAT" in German text (warning)

`VAT` becomes `USt.` (Umsatzsteuer). The English abbreviation in
a German invoice or offer reads as untranslated boilerplate.
Warning, because a text that quotes an English form or an
EU-wide document may legitimately keep `VAT`.

## GFC-15 day number without a dot (error)

`20 November 2026` becomes `20. November 2026` — the German
long date puts a dot after the day number. The rule also maps an
English month in the same span (`20 March 2026` → `20. März
2026`) so the date is fixed in one pass. `20. November 2026` is
never flagged.

## How overlaps are resolved

Rules run composite-first (currency, US date, day+month, phone,
postal, unit, time, ordinal, month, decimal, thousands, percent,
ASCII, quotes, VAT), and a finding never overlaps a span an
earlier rule already claimed. `fix()` then applies the fixes and
re-checks, up to 6 passes, so a fix that exposes a new finding
(a postal fix that reveals an ASCII substitute in the city name,
a month fix that reveals a missing dot) is caught on the next
pass. The test suite asserts the round-trip: `fix()` output
re-checks to zero findings on every test vector.
