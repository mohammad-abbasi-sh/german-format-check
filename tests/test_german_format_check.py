"""Tests for german-format-check — every GFC rule with a positive and a
negative vector, fix round-trips, the four formatters, and the CLI.
Run: python3 -m pytest tests/test_german_format_check.py -q
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "skills" / "german-format-check" / "scripts"))
from german_format_check import (  # noqa: E402
    check, fix, format_date, format_money, format_number, format_phone,
)

HERE = Path(__file__).resolve().parent
TOOL = (HERE.parent / "skills" / "german-format-check" / "scripts"
        / "german_format_check.py")


def codes(text):
    return [f["code"] for f in check(text)]


def codes_of(text, code):
    return [f for f in check(text) if f["code"] == code]


# ---------------------------------------------------------------------------
# GFC-01 English decimal point
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["29.99", "Der Preis ist 29.99 Euro.",
                                  "Pi ist 3.14.", "1,234.56 Euro"])
def test_gfc01_positive(text):
    assert "GFC-01" in codes(text)


@pytest.mark.parametrize("text", ["29,99", "1.234,56", "20.11.2026",
                                  "2026-11-20", "1.234 Euro",
                                  "Die Version ist 2.0.1."])
def test_gfc01_negative(text):
    assert "GFC-01" not in codes(text)


def test_gfc01_fix():
    assert fix("29.99 Euro") == "29,99 Euro"
    assert fix("1,234.56 Euro") == "1.234,56 Euro"


# ---------------------------------------------------------------------------
# GFC-02 English thousands comma
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["1,234 Personen", "1,000,000 Euro"])
def test_gfc02_positive(text):
    assert "GFC-02" in codes(text)


@pytest.mark.parametrize("text", ["1.234 Personen", "1.234,56 Euro"])
def test_gfc02_negative(text):
    assert "GFC-02" not in codes(text)


def test_gfc02_fix():
    assert fix("1,234 Personen") == "1.234 Personen"
    assert fix("1,000,000 Euro") == "1.000.000 Euro"


# ---------------------------------------------------------------------------
# GFC-03 currency before the amount
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["€29.99", "$19.99", "EUR 29.99",
                                  "€ 29.99", "Der Preis: $19.99."])
def test_gfc03_positive(text):
    assert "GFC-03" in codes(text)


@pytest.mark.parametrize("text", ["29,99 €", "19,99 $"])
def test_gfc03_negative(text):
    assert "GFC-03" not in codes(text)


def test_gfc03_fix_also_fixes_decimal():
    # One finding, not two: GFC-03 claims the whole span, GFC-01 stays out.
    assert codes("€29.99") == ["GFC-03"]
    assert fix("€29.99") == "29,99 €"
    assert fix("EUR 29.99") == "29,99 €"
    assert fix("$19.99") == "19,99 $"


# ---------------------------------------------------------------------------
# GFC-04 US date
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("11/20/2026", "20.11.2026"), ("2026/11/20", "20.11.2026"),
    ("November 20, 2026", "20.11.2026"), ("Nov 20, 2026", "20.11.2026"),
    ("March 5, 2026", "05.03.2026"),
])
def test_gfc04_positive(text, expected):
    found = codes_of(text, "GFC-04")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["20.11.2026", "2026-11-20",
                                  "20. November 2026"])
def test_gfc04_negative(text):
    assert "GFC-04" not in codes(text)


def test_gfc04_month_name_not_double_flagged():
    # "March 5, 2026" is one GFC-04 finding, not GFC-04 + GFC-10.
    assert codes("March 5, 2026") == ["GFC-04"]


# ---------------------------------------------------------------------------
# GFC-05 12-hour time
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("2:30 PM", "14:30 Uhr"), ("2:30pm", "14:30 Uhr"),
    ("9:15 AM", "09:15 Uhr"), ("12:00 AM", "00:00 Uhr"),
    ("12:30 PM", "12:30 Uhr"), ("11:59 p.m.", "23:59 Uhr"),
])
def test_gfc05_positive(text, expected):
    found = codes_of(text, "GFC-05")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["14:30 Uhr", "09:15 Uhr", "14:30"])
def test_gfc05_negative(text):
    assert "GFC-05" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-06 percent without space (warning)
# ---------------------------------------------------------------------------

def test_gfc06_positive():
    found = codes_of("19% Rabatt", "GFC-06")
    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert fix("19% Rabatt") == "19 % Rabatt"


def test_gfc06_negative():
    assert codes("19 % Rabatt") == []


# ---------------------------------------------------------------------------
# GFC-07 US-style phone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("(030) 123-4567", "030 1234567"),
    ("+49-30-1234567", "+49 30 1234567"),
    ("030-1234567", "030 1234567"),
])
def test_gfc07_positive(text, expected):
    found = codes_of(text, "GFC-07")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["+49 30 12345678", "030 1234567",
                                  "(030) 1234567"])
def test_gfc07_negative(text):
    assert "GFC-07" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-08 postal code
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("D-10115 Berlin", "10115"), ("Berlin, 10115", "10115 Berlin"),
    ("München, 80331", "80331 München"),
])
def test_gfc08_positive(text, expected):
    found = codes_of(text, "GFC-08")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["10115 Berlin", "80331 München"])
def test_gfc08_negative(text):
    assert "GFC-08" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-09 ASCII substitutes for umlaut / ß (warning)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Strasse", "Straße"), ("Muenchen", "München"), ("Koeln", "Köln"),
    ("weiss", "weiß"), ("gross", "groß"), ("Fuss", "Fuß"),
    ("Gruss", "Gruß"), ("Maedchen", "Mädchen"),
])
def test_gfc09_positive(text, expected):
    found = codes_of(text, "GFC-09")
    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["Straße", "München", "Köln", "weiß",
                                  "groß", "Fuß", "Gruß", "Mädchen"])
def test_gfc09_negative(text):
    assert "GFC-09" not in codes(text)


def test_gfc09_case_aware():
    assert fix("Muenchen ist schoen.") == "München ist schoen."
    assert fix("WEISS") == "WEIẞ"  # capital sharp-s, not "WEISS"


# ---------------------------------------------------------------------------
# GFC-10 English month names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("January", "Januar"), ("February", "Februar"), ("March", "März"),
    ("May", "Mai"), ("June", "Juni"), ("July", "Juli"),
    ("October", "Oktober"),
])
def test_gfc10_positive(text, expected):
    found = codes_of(text, "GFC-10")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["November", "December", "August",
                                  "September", "April", "Januar", "März"])
def test_gfc10_negative(text):
    # November/December/August/September/April are spelled the same
    # in English and German — flagging them would be a false positive.
    assert "GFC-10" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-11 English ordinals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("1st", "1."), ("2nd", "2."), ("3rd", "3."), ("4th", "4."),
])
def test_gfc11_positive(text, expected):
    found = codes_of(text, "GFC-11")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["1.", "2. Platz", "am 4. Mai"])
def test_gfc11_negative(text):
    assert "GFC-11" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-12 straight double quotes (warning)
# ---------------------------------------------------------------------------

def test_gfc12_positive():
    found = codes_of('Er sagte "Hallo".', "GFC-12")
    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert fix('Er sagte "Hallo".') == "Er sagte „Hallo“."


@pytest.mark.parametrize("text", ["Er sagte „Hallo“.", "Er sagte 'Hallo'."])
def test_gfc12_negative(text):
    assert "GFC-12" not in codes(text)


def test_gfc12_unpaired_quote_not_flagged():
    assert codes('Er sagte "Hallo.') == []


# ---------------------------------------------------------------------------
# GFC-13 missing space before unit
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("20°C", "20 °C"), ("10km", "10 km"), ("5kg", "5 kg"), ("3m", "3 m"),
])
def test_gfc13_positive(text, expected):
    found = codes_of(text, "GFC-13")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["20 °C", "10 km", "5 kg", "3 m"])
def test_gfc13_negative(text):
    assert "GFC-13" not in codes(text)


# ---------------------------------------------------------------------------
# GFC-14 VAT
# ---------------------------------------------------------------------------

def test_gfc14_positive():
    found = codes_of("Preis inkl. VAT", "GFC-14")
    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert fix("Preis inkl. VAT") == "Preis inkl. USt."


def test_gfc14_negative():
    assert codes("Preis inkl. USt.") == []


# ---------------------------------------------------------------------------
# GFC-15 day number without a dot
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("20 November 2026", "20. November 2026"),
    ("20 March 2026", "20. März 2026"),
    ("1 January 2026", "1. Januar 2026"),
])
def test_gfc15_positive(text, expected):
    found = codes_of(text, "GFC-15")
    assert len(found) == 1
    assert found[0]["fix"] == expected


@pytest.mark.parametrize("text", ["20. November 2026", "20.11.2026"])
def test_gfc15_negative(text):
    assert "GFC-15" not in codes(text)


# ---------------------------------------------------------------------------
# Finding shape, ordering, fix round-trips
# ---------------------------------------------------------------------------

def test_finding_shape_and_order():
    findings = check("€29.99 am 11/20/2026")
    assert findings[0]["code"] == "GFC-03"
    assert findings[1]["code"] == "GFC-04"
    for f in findings:
        assert set(f) == {"code", "message", "severity", "start", "end",
                          "span", "fix"}
        assert f["span"] == [f["start"], f["end"]]
        assert f["severity"] in ("error", "warning")
        assert f["start"] < f["end"]


def test_no_double_reporting_on_overlap():
    # One piece of text is reported once, under the most specific rule.
    assert codes("€29.99") == ["GFC-03"]
    assert codes("March 5, 2026") == ["GFC-04"]
    assert codes("20 March 2026") == ["GFC-15"]
    assert codes("1,234.56") == ["GFC-01"]


def test_fix_round_trip_demo_paragraph():
    text = (HERE / "fixtures" / "sample-de.txt").read_text(encoding="utf-8")
    findings = check(text)
    assert len(findings) == 8
    assert sum(1 for f in findings if f["severity"] == "error") == 5
    assert sum(1 for f in findings if f["severity"] == "warning") == 3
    fixed = fix(text)
    assert check(fixed) == []
    assert "29,99 €" in fixed and "20.11.2026" in fixed
    assert "14:30 Uhr" in fixed and "München" in fixed
    assert "Straße" in fixed and "10 km" in fixed and "19 %" in fixed
    assert "030 1234567" in fixed


def test_fix_round_trip_clean_fixture():
    text = (HERE / "fixtures" / "sample-clean-de.txt").read_text(
        encoding="utf-8")
    assert check(text) == []
    assert fix(text) == text


@pytest.mark.parametrize("text", [
    "29.99", "1,234", "EUR 29.99", "11/20/2026", "2:30 PM", "19%",
    "(030) 123-4567", "D-10115", "Muenchen", "January", "1st",
    '"Hallo"', "20°C", "VAT", "20 November 2026",
])
def test_fix_round_trip_each_rule(text):
    fixed = fix(text)
    assert check(fixed) == [], "fix(%r) = %r still has findings" % (
        text, fixed)


def test_fix_is_idempotent():
    text = "€29.99 am November 20, 2026 um 2:30 PM in Muenchen."
    assert fix(fix(text)) == fix(text)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (1234.56, "1.234,56"), (1234.5, "1.234,5"), (1234, "1.234"),
    (0, "0"), (-1234.56, "-1.234,56"), (1234567.89, "1.234.567,89"),
    (29.99, "29,99"), ("1234.56", "1.234,56"), (1000000, "1.000.000"),
])
def test_format_number(value, expected):
    assert format_number(value) == expected


def test_format_number_rejects_non_numbers():
    with pytest.raises(ValueError):
        format_number("abc")
    with pytest.raises(ValueError):
        format_number(None)


@pytest.mark.parametrize("value,currency,expected", [
    (29.99, "EUR", "29,99 €"), (19.99, "USD", "19,99 $"),
    (5, "CHF", "5,00 CHF"), (10, "GBP", "10,00 £"),
    (29.995, "EUR", "30,00 €"), (0, "EUR", "0,00 €"),
])
def test_format_money(value, currency, expected):
    assert format_money(value, currency) == expected


def test_format_money_default_currency_is_eur():
    assert format_money(29.99) == "29,99 €"


@pytest.mark.parametrize("value,expected", [
    ("2026-11-20", "20.11.2026"), (date(2026, 11, 20), "20.11.2026"),
    ("20.11.2026", "20.11.2026"),
])
def test_format_date_short(value, expected):
    assert format_date(value) == expected


def test_format_date_long():
    assert format_date("2026-11-20", long=True) == "20. November 2026"
    assert format_date(date(2026, 3, 5), long=True) == "5. März 2026"


def test_format_date_rejects_garbage():
    with pytest.raises(ValueError):
        format_date("20 November 2026")
    with pytest.raises(ValueError):
        format_date("not a date")


@pytest.mark.parametrize("value,expected", [
    ("+493012345678", "+49 30 12345678"),
    ("+4915112345678", "+49 151 12345678"),
    ("0301234567", "030 1234567"),
    ("+49891234567", "+49 89 1234567"),
    ("00493012345678", "+49 30 12345678"),
])
def test_format_phone(value, expected):
    assert format_phone(value) == expected


def test_format_phone_rejects_garbage():
    with pytest.raises(ValueError):
        format_phone("123")
    with pytest.raises(ValueError):
        format_phone("not a phone")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_cli(args, input_text=None):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          input=input_text, capture_output=True, text=True,
                          timeout=60)


def test_cli_check_clean_fixture_exits_0():
    proc = _run_cli(["check", str(HERE / "fixtures"
                                  / "sample-clean-de.txt")])
    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_cli_check_dirty_fixture_exits_1():
    proc = _run_cli(["check", str(HERE / "fixtures" / "sample-de.txt")])
    assert proc.returncode == 1
    assert "GFC-03" in proc.stdout
    assert "5 error(s), 3 warning(s)" in proc.stdout


def test_cli_check_warnings_only_exits_0_without_strict():
    proc = _run_cli(["check"], input_text="19% Rabatt in Muenchen.")
    assert proc.returncode == 0


def test_cli_check_warnings_fail_with_strict():
    proc = _run_cli(["check", "--strict"], input_text="19% Rabatt.")
    assert proc.returncode == 1


def test_cli_check_json_output():
    proc = _run_cli(["check", "--json"], input_text="Der Preis ist 29.99.")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["errors"] == 1
    assert data["findings"][0]["code"] == "GFC-01"
    assert data["findings"][0]["fix"] == "29,99"


def test_cli_check_stdin_dash():
    proc = _run_cli(["check", "-"], input_text="29.99 Euro")
    assert proc.returncode == 1
    assert "GFC-01" in proc.stdout


def test_cli_fix_prints_fixed_text():
    proc = _run_cli(["fix"], input_text="Der Preis ist 29.99 Euro.")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "Der Preis ist 29,99 Euro."


def test_cli_format_commands():
    assert _run_cli(["format-number", "1234.56"]).stdout.strip() == "1.234,56"
    assert _run_cli(["format-money", "29.99",
                     "EUR"]).stdout.strip() == "29,99 €"
    assert _run_cli(["format-date",
                     "2026-11-20"]).stdout.strip() == "20.11.2026"
    assert _run_cli(["format-date", "2026-11-20",
                     "--long"]).stdout.strip() == "20. November 2026"
    assert _run_cli(["format-phone",
                     "+493012345678"]).stdout.strip() == "+49 30 12345678"


def test_cli_missing_file_exits_2():
    proc = _run_cli(["check", "does-not-exist.txt"])
    assert proc.returncode == 2


def test_cli_format_invalid_exits_2():
    proc = _run_cli(["format-number", "abc"])
    assert proc.returncode == 2
