#!/usr/bin/env python3
"""german-format-check — catch English-style formatting inside German text.

Zero-dependency (Python standard library only). One deterministic checker
for the formatting mistakes agents make when they write German the way
they write English: English decimals (29.99), US dates (11/20/2026),
12-hour times (2:30 PM), currency before the amount (EUR 29.99), ASCII
substitutes for umlauts (Muenchen), English month names (January),
straight quotes ("..."), missing spaces before units (20°C) — 15 rules
(GFC-01..GFC-15), each with an automatic fix.

Public API:
    check(text) -> list of findings
        {"code", "message", "severity", "start", "end", "span", "fix"}
        severity is "error" or "warning"; "fix" is the replacement text
        for text[start:end] (None when no safe automatic fix exists).
    fix(text) -> fixed text (applies fixes, re-checks, repeats until
        clean or the text stops changing)
    format_number(value)  -> "1.234,56"
    format_money(value, currency="EUR") -> "29,99 €"
    format_date(value, long=False) -> "20.11.2026" / "20. November 2026"
    format_phone(value) -> "+49 30 12345678"

CLI:
    check [--json] [--strict] [file|-]     exit 0 clean, 1 errors found
                                            (warnings fail only with
                                            --strict), 2 usage error
    fix [file|-]                            print the fixed text
    format-number VALUE
    format-money VALUE [CURRENCY]
    format-date VALUE [--long]
    format-phone VALUE

Rules (see skills/german-format-check/references/formatting-rules.md
for the reasoning behind each one):
    GFC-01 English decimal point      29.99 -> 29,99 (error)
    GFC-02 English thousands comma    1,234 -> 1.234 (error)
    GFC-03 currency before amount     EUR 29.99 -> 29,99 € (error)
    GFC-04 US date                    11/20/2026 -> 20.11.2026 (error)
    GFC-05 12-hour time               2:30 PM -> 14:30 Uhr (error)
    GFC-06 percent without space      19% -> 19 % (warning, DIN 5008)
    GFC-07 US-style phone             (030) 123-4567 -> 030 1234567 (error)
    GFC-08 postal code                D-10115 -> 10115 (error)
    GFC-09 ASCII umlaut substitutes   Muenchen -> München (warning)
    GFC-10 English month names        January -> Januar (error)
    GFC-11 English ordinals           1st -> 1. (error)
    GFC-12 straight double quotes     "..." -> „..." (warning)
    GFC-13 missing space before unit  20°C -> 20 °C (error)
    GFC-14 "VAT" in German text       VAT -> USt. (warning)
    GFC-15 day without dot            20 November 2026 -> 20. November 2026

Deliberate non-flags: ISO dates (2026-11-20) are fine in code and
prose; German dates (20.11.2026) and German numbers (1.234,56) are
never flagged; November, December, August, September and April are
spelled the same in English and German and are never flagged.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Shared tables
# ---------------------------------------------------------------------------

DE_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

# English month name -> (German name, month number). Only the months whose
# English spelling differs from German are flagged by GFC-10; the others
# (April, August, September, November, December) are identical and are
# never flagged.
EN_MONTHS = {
    "january": ("Januar", 1), "february": ("Februar", 2),
    "march": ("März", 3), "may": ("Mai", 5),
    "june": ("Juni", 6), "july": ("Juli", 7),
    "october": ("Oktober", 10),
}
EN_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11,
    "dec": 12,
}
ALL_EN_MONTHS = {**{k: v[1] for k, v in EN_MONTHS.items()},
                 "april": 4, "august": 8, "september": 9,
                 "november": 11, "december": 12, **EN_MONTH_ABBR}

# ASCII substitutes -> German spelling (GFC-09, warning only: ASCII
# contexts such as URLs, e-mail addresses and code legitimately use them).
ASCII_SUBSTITUTES = {
    "strasse": "straße", "muenchen": "münchen", "koeln": "köln",
    "weiss": "weiß", "gross": "groß", "fuss": "fuß",
    "gruss": "gruß", "maedchen": "mädchen",
}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}

UNITS = ("°C", "km", "cm", "mm", "mg", "ml", "kg", "g", "m", "l")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _group_thousands(int_part):
    """Group an integer string in threes with dots: 1234567 -> 1.234.567."""
    out = []
    while len(int_part) > 3:
        out.append(int_part[-3:])
        int_part = int_part[:-3]
    out.append(int_part)
    return ".".join(reversed(out))


def format_number(value):
    """Format a number the German way: 1234.56 -> "1.234,56".

    Accepts int, float or a numeric string with a "." decimal point.
    The fractional part is preserved as given (1234.5 -> "1.234,5").
    Negative numbers keep their sign; zero formats as "0".
    """
    if isinstance(value, bool):
        raise ValueError("format_number needs a number, got a boolean")
    if isinstance(value, Decimal):
        text = format(value, "f")
    elif isinstance(value, (int, float)):
        text = repr(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError("format_number needs a number, got %r" % (value,))
    if not re.fullmatch(r"[+-]?(\d+(\.\d+)?|\.\d+)", text):
        raise ValueError("not a number: %r" % (value,))
    sign = ""
    if text.startswith(("+", "-")):
        sign, text = text[0], text[1:]
        if sign == "+":
            sign = ""
    if "." in text:
        int_part, frac_part = text.split(".", 1)
    else:
        int_part, frac_part = text, ""
    int_part = int_part.lstrip("0") or "0"
    grouped = _group_thousands(int_part)
    if frac_part:
        return "%s%s,%s" % (sign, grouped, frac_part)
    return "%s%s" % (sign, grouped)


def format_money(value, currency="EUR"):
    """Format money the German way: 29.99 EUR -> "29,99 €".

    Always two decimals (rounded half-up). The currency symbol goes
    after the amount, separated by a space (DIN 5008).
    """
    try:
        amount = Decimal(str(value))
    except Exception:
        raise ValueError("not a number: %r" % (value,))
    symbol = CURRENCY_SYMBOLS.get(str(currency).upper(), str(currency))
    rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = format_number(rounded)
    return "%s %s" % (text, symbol)


def _parse_date(value):
    """Accept a date/datetime, "2026-11-20" or "20.11.2026"."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    raise ValueError("not a date (use YYYY-MM-DD or DD.MM.YYYY): %r"
                     % (value,))


def format_date(value, long=False):
    """Format a date the German way: 2026-11-20 -> "20.11.2026".

    With long=True: "20. November 2026".
    """
    d = _parse_date(value)
    if long:
        return "%d. %s %d" % (d.day, DE_MONTHS[d.month - 1], d.year)
    return "%02d.%02d.%d" % (d.day, d.month, d.year)


def format_phone(value):
    """Format a German phone number: +493012345678 -> "+49 30 12345678".

    Area-code length is a heuristic: 2 digits for the large cities
    (30 Berlin, 40 Hamburg, 69 Frankfurt, 89 München), 3 digits for
    mobiles (15x/16x/17x) and most other landlines. The subscriber
    part is left as one block, which is the DIN 5008 style.
    """
    text = re.sub(r"[\s().-]", "", str(value).strip())
    country = None
    if text.startswith("+49"):
        country, national = "+49", text[3:]
    elif text.startswith("0049"):
        country, national = "+49", text[4:]
    elif text.startswith("49") and len(text) > 10:
        country, national = "+49", text[2:]
    elif text.startswith("0"):
        country, national = None, text[1:]
    else:
        raise ValueError("not a German phone number: %r" % (value,))
    if not national.isdigit() or len(national) < 6:
        raise ValueError("not a German phone number: %r" % (value,))
    if national.startswith("1"):
        area_len = 3  # mobile: 151, 160, 171, ...
    elif national[:2] in ("30", "40", "69", "89"):
        area_len = 2
    else:
        area_len = 3
    area, rest = national[:area_len], national[area_len:]
    if country:
        return "%s %s %s" % (country, area, rest)
    return "0%s %s" % (area, rest)


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

def _finding(code, message, severity, start, end, fix):
    return {"code": code, "message": message, "severity": severity,
            "start": start, "end": end, "span": [start, end], "fix": fix}


def _preserve_case(original, replacement):
    """Apply the original word's capitalisation to the replacement."""
    if original.isupper():
        return replacement.replace("ß", "ẞ").upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _en_number_to_de(matched):
    """Convert an English-format number to German: 1,234.56 -> 1.234,56."""
    text = matched.replace(",", "")
    if "." in text:
        int_part, frac = text.split(".", 1)
    else:
        int_part, frac = text, ""
    grouped = _group_thousands(int_part.lstrip("0") or "0")
    return "%s,%s" % (grouped, frac) if frac else grouped


# -- individual rules; each appends findings, skipping spans already taken
#    by an earlier (larger / composite) rule, so one piece of text is
#    never reported twice.

def _rule_currency(text, findings, taken):
    # €29.99 / $19.99 / EUR 29.99 / € 29.99 -> 29,99 € (also fixes decimal)
    pat = re.compile(r"(€|\$|EUR)\s?(\d[\d,]*\.?\d*)")
    for m in pat.finditer(text):
        sym, amount = m.group(1), m.group(2)
        if "." not in amount and "," not in amount:
            continue  # bare "€29" has no formatting error to fix
        fixed_amount = _en_number_to_de(amount)
        symbol = "€" if sym in ("€", "EUR") else "$"
        findings.append(_finding(
            "GFC-03", "Currency symbol before the amount: %r -> %r"
            % (m.group(0), "%s %s" % (fixed_amount, symbol)),
            "error", m.start(), m.end(),
            "%s %s" % (fixed_amount, symbol)))
        taken.append((m.start(), m.end()))


def _rule_us_date(text, findings, taken):
    def _emit(m, day, month, year):
        fixed = "%02d.%02d.%d" % (day, month, year)
        findings.append(_finding(
            "GFC-04", "US date: %r -> %r" % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))

    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            _emit(m, day, month, year)
    for m in re.finditer(r"\b(\d{4})/(\d{1,2})/(\d{1,2})\b", text):
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            _emit(m, day, month, year)
    month_names = "|".join(sorted(ALL_EN_MONTHS, key=len, reverse=True))
    pat = re.compile(r"\b(%s)\.?\s+(\d{1,2}),\s*(\d{4})\b"
                     % month_names, re.IGNORECASE)
    for m in pat.finditer(text):
        month = ALL_EN_MONTHS[m.group(1).lower().rstrip(".")]
        day, year = int(m.group(2)), int(m.group(3))
        if 1 <= day <= 31:
            _emit(m, day, month, year)


def _rule_day_month(text, findings, taken):
    # 20 November 2026 / 20 March 2026 -> 20. November 2026 / 20. März 2026
    de = "|".join(DE_MONTHS)
    en = "|".join(sorted(EN_MONTHS, key=len, reverse=True))
    pat = re.compile(r"\b(\d{1,2})\s+(%s|%s)\s+(\d{4})\b" % (de, en),
                     re.IGNORECASE)
    for m in pat.finditer(text):
        day, month_word, year = int(m.group(1)), m.group(2), m.group(3)
        german = EN_MONTHS.get(month_word.lower(), (month_word, None))[0]
        fixed = "%d. %s %s" % (day, german, year)
        findings.append(_finding(
            "GFC-15", "Day number without a dot: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_phone(text, findings, taken):
    def _emit(m, fixed):
        findings.append(_finding(
            "GFC-07", "US-style phone number: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))

    for m in re.finditer(r"\(\d{2,5}\)\s*\d[\d\s-]*-\d[\d\s-]*\d", text):
        fixed = re.sub(r"[()]", "", m.group(0))
        fixed = fixed.replace("-", "")
        fixed = re.sub(r"\s+", " ", fixed).strip()
        _emit(m, fixed)
    for m in re.finditer(r"\+\d{1,3}(?:-\d+){2,}", text):
        _emit(m, m.group(0).replace("-", " "))
    for m in re.finditer(r"\b0\d{2,4}-\d[\d\s-]*\d\b", text):
        _emit(m, m.group(0).replace("-", " "))


def _rule_postal(text, findings, taken):
    for m in re.finditer(r"\bD-(\d{5})\b", text):
        findings.append(_finding(
            "GFC-08", "Obsolete 'D-' postal prefix (dropped in 1993): "
            "%r -> %r" % (m.group(0), m.group(1)),
            "error", m.start(), m.end(), m.group(1)))
        taken.append((m.start(), m.end()))
    pat = re.compile(r"\b([A-ZÄÖÜ][a-zäöüß]+),\s*(\d{5})\b")
    for m in pat.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        fixed = "%s %s" % (m.group(2), m.group(1))
        findings.append(_finding(
            "GFC-08", "Postal code after the city: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_unit(text, findings, taken):
    pat = re.compile(r"(\d+(?:\.\d+)?)(%s)\b" % "|".join(
        re.escape(u) for u in UNITS))
    for m in pat.finditer(text):
        fixed = "%s %s" % (m.group(1), m.group(2))
        findings.append(_finding(
            "GFC-13", "Missing space before unit: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_time(text, findings, taken):
    pat = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]\.?")
    for m in pat.finditer(text):
        hour, minute, ampm = int(m.group(1)), m.group(2), m.group(3).upper()
        if not (1 <= hour <= 12 and 0 <= int(minute) <= 59):
            continue
        if ampm == "A":
            hour24 = 0 if hour == 12 else hour
        else:
            hour24 = 12 if hour == 12 else hour + 12
        fixed = "%02d:%s Uhr" % (hour24, minute)
        findings.append(_finding(
            "GFC-05", "12-hour time: %r -> %r" % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_ordinal(text, findings, taken):
    for m in re.finditer(r"\b(\d+)(st|nd|rd|th)\b", text):
        fixed = "%s." % m.group(1)
        findings.append(_finding(
            "GFC-11", "English ordinal: %r -> %r" % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_month(text, findings, taken):
    pat = re.compile(r"\b(%s)\b" % "|".join(EN_MONTHS), re.IGNORECASE)
    for m in pat.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        german = EN_MONTHS[m.group(1).lower()][0]
        fixed = _preserve_case(m.group(1), german)
        findings.append(_finding(
            "GFC-10", "English month name: %r -> %r"
            % (m.group(1), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_decimal(text, findings, taken):
    # English decimal: 29.99 / 3.14 / 1,234.56. Deliberately NOT matched:
    # German dates (20.11.2026), German numbers (1.234,56) and German
    # thousands (1.234) — the lookarounds and the 1-2 digit fractional
    # part keep those out.
    pat = re.compile(
        r"(?<!\d\.)(?:\d{1,3}(?:,\d{3})+\.\d+|\d+\.\d{1,2})(?!\.\d)(?!,?\d)")
    for m in pat.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        fixed = _en_number_to_de(m.group(0))
        findings.append(_finding(
            "GFC-01", "English decimal point: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_thousands(text, findings, taken):
    pat = re.compile(r"\b\d{1,3}(?:,\d{3})+(?!\.\d)(?!,?\d)")
    for m in pat.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        fixed = m.group(0).replace(",", ".")
        findings.append(_finding(
            "GFC-02", "English thousands comma: %r -> %r"
            % (m.group(0), fixed),
            "error", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_percent(text, findings, taken):
    for m in re.finditer(r"\d+(?:[.,]\d+)?%", text):
        findings.append(_finding(
            "GFC-06", "Percent without a space (DIN 5008): %r -> %r"
            % (m.group(0), m.group(0)[:-1] + " %"),
            "warning", m.start(), m.end(), m.group(0)[:-1] + " %"))
        taken.append((m.start(), m.end()))


def _rule_ascii(text, findings, taken):
    pat = re.compile(r"\b(%s)\b" % "|".join(ASCII_SUBSTITUTES),
                     re.IGNORECASE)
    for m in pat.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        fixed = _preserve_case(
            m.group(1), ASCII_SUBSTITUTES[m.group(1).lower()])
        findings.append(_finding(
            "GFC-09", "ASCII substitute for umlaut/ß: %r -> %r"
            % (m.group(1), fixed),
            "warning", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_quotes(text, findings, taken):
    for m in re.finditer(r'"([^"\n]{1,200})"', text):
        fixed = "„%s“" % m.group(1)
        findings.append(_finding(
            "GFC-12", "Straight double quotes in German prose: "
            "%r -> %r" % (m.group(0), fixed),
            "warning", m.start(), m.end(), fixed))
        taken.append((m.start(), m.end()))


def _rule_vat(text, findings, taken):
    for m in re.finditer(r"\bVAT\b", text):
        findings.append(_finding(
            "GFC-14", '"VAT" in German text: use "USt."',
            "warning", m.start(), m.end(), "USt."))
        taken.append((m.start(), m.end()))


# Composite rules first (they claim the largest spans), then the
# single-token rules. check() dedups by span, so a piece of text is
# reported once, under the most specific rule.
_RULES = (
    _rule_currency, _rule_us_date, _rule_day_month, _rule_phone,
    _rule_postal, _rule_unit, _rule_time, _rule_ordinal, _rule_month,
    _rule_decimal, _rule_thousands, _rule_percent, _rule_ascii,
    _rule_quotes, _rule_vat,
)


def check(text):
    """Return the list of findings for *text*, sorted by position."""
    findings, taken = [], []
    for rule in _RULES:
        rule(text, findings, taken)
    findings.sort(key=lambda f: (f["start"], f["end"]))
    return findings


def fix(text):
    """Apply all fixes, re-check, and repeat until clean.

    Re-checking between passes is what makes composite fixes safe:
    a currency fix also repairs the decimal inside it, a date fix
    also repairs the month name inside it, and a postal fix does not
    stop the umlaut inside the city name from being fixed on the
    next pass. Stops after 6 passes or when the text stops changing.
    """
    current = text
    for _ in range(6):
        findings = check(current)
        if not findings:
            break
        fixed = current
        for f in sorted(findings, key=lambda x: x["start"], reverse=True):
            if f["fix"] is None:
                continue
            fixed = fixed[:f["start"]] + f["fix"] + fixed[f["end"]:]
        if fixed == current:
            break
        current = fixed
    return current


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_input(path):
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _cmd_check(args):
    text = _read_input(args.file)
    findings = check(text)
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = len(findings) - errors
    if args.json:
        print(json.dumps({"findings": findings, "errors": errors,
                          "warnings": warnings},
                         ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: no formatting issues found.")
        for f in findings:
            print("%s [%s] (%d-%d): %s"
                  % (f["code"], f["severity"], f["start"], f["end"],
                     f["message"]))
        print("%d error(s), %d warning(s)." % (errors, warnings))
    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


def _cmd_fix(args):
    text = _read_input(args.file)
    print(fix(text), end="" if text.endswith("\n") else "\n")
    return 0


def _cmd_format_number(args):
    try:
        print(format_number(args.value))
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


def _cmd_format_money(args):
    try:
        print(format_money(args.value, args.currency))
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


def _cmd_format_date(args):
    try:
        print(format_date(args.value, long=args.long))
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


def _cmd_format_phone(args):
    try:
        print(format_phone(args.value))
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="german_format_check",
        description="Catch English-style formatting inside German text.")
    parser.add_argument("--version", action="version",
                        version="german-format-check %s" % VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="check text for formatting issues")
    p.add_argument("file", nargs="?", default="-",
                   help="file to check, or - / omit for stdin")
    p.add_argument("--json", action="store_true",
                   help="machine-readable output")
    p.add_argument("--strict", action="store_true",
                   help="warnings also fail the build (exit 1)")
    p.set_defaults(func=_cmd_check)

    p = sub.add_parser("fix", help="print the fixed text")
    p.add_argument("file", nargs="?", default="-",
                   help="file to fix, or - / omit for stdin")
    p.set_defaults(func=_cmd_fix)

    p = sub.add_parser("format-number", help="1234.56 -> 1.234,56")
    p.add_argument("value")
    p.set_defaults(func=_cmd_format_number)

    p = sub.add_parser("format-money", help="29.99 EUR -> 29,99 €")
    p.add_argument("value")
    p.add_argument("currency", nargs="?", default="EUR")
    p.set_defaults(func=_cmd_format_money)

    p = sub.add_parser("format-date", help="2026-11-20 -> 20.11.2026")
    p.add_argument("value")
    p.add_argument("--long", action="store_true",
                   help='long form: "20. November 2026"')
    p.set_defaults(func=_cmd_format_date)

    p = sub.add_parser("format-phone", help="+493012345678 -> +49 30 12345678")
    p.add_argument("value")
    p.set_defaults(func=_cmd_format_phone)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except UnicodeDecodeError as exc:
        print("error: cannot read file as UTF-8: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
