# Examples — before / after

Each example shows the checker's output and the fixed text. All of
them are covered by tests in `tests/test_german_format_check.py`.

## 1. A product description with five errors

Before:

```text
Der Preis ist €29.99 und das Treffen ist am November 20, 2026 um 2:30 PM in Muenchen. Die Strasse ist 10km lang und kostet 19% mehr. Rufen Sie (030) 123-4567 an.
```

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
```

After (`fix`, then `check` exits 0):

```text
Der Preis ist 29,99 € und das Treffen ist am 20.11.2026 um 14:30 Uhr in München. Die Straße ist 10 km lang und kostet 19 % mehr. Rufen Sie 030 1234567 an.
```

## 2. An invoice line

Before: `Rechnung: EUR 29.99, VAT inklusive, fällig am 11/20/2026.`

After: `Rechnung: 29,99 €, USt. inklusive, fällig am 20.11.2026.`

Three rules in one line — GFC-03 (currency + decimal), GFC-14
(VAT, warning), GFC-04 (US date) — and the fix applies all three
without touching the rest.

## 3. An address block

Before:

```text
Muster GmbH
D-10115 Berlin, Germany
```

After:

```text
Muster GmbH
10115 Berlin, Germany
```

GFC-08 drops the obsolete `D-` prefix. (`Berlin, 10115` — the
code after the city — is the same rule's second case.)

## 4. A date and time in running text

Before: `Das 1st Treffen ist am 20 March 2026 um 9:15 AM.`

After: `Das 1. Treffen ist am 20. März 2026 um 09:15 Uhr.`

GFC-11 (ordinal), GFC-15 (day without a dot, which also maps the
English month), GFC-05 (12-hour time).

## 5. A quote and a temperature

Before: `Er sagte "Es ist 20°C warm".`

After: `Er sagte „Es ist 20 °C warm“.`

GFC-12 (straight quotes, warning) and GFC-13 (space before the
unit).

## 6. What is NOT flagged

```text
Der Preis ist 29,99 €. Am 20.11.2026 um 14:30 Uhr in München.
Die Straße ist 10 km lang. Das ISO-Datum 2026-11-20 ist in Ordnung.
Die Zahl 1.234,56 stimmt.
```

`check` on this text exits 0 with `OK: no formatting issues
found.` German dates, German numbers, an ISO date in a technical
context and a correctly written umlaut are all left alone.

## 7. Formatters

```bash
$ python3 scripts/german_format_check.py format-number 1234.56
1.234,56
$ python3 scripts/german_format_check.py format-money 29.99 EUR
29,99 €
$ python3 scripts/german_format_check.py format-date 2026-11-20
20.11.2026
$ python3 scripts/german_format_check.py format-date 2026-11-20 --long
20. November 2026
$ python3 scripts/german_format_check.py format-phone +493012345678
+49 30 12345678
```
