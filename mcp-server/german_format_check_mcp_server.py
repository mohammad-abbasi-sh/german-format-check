#!/usr/bin/env python3
"""MCP server for german-format-check — expose the German formatting
checker as tools for any MCP client.

Zero-dependency (Python standard library only). Speaks JSON-RPC 2.0
over stdio, newline-delimited, following the MCP lifecycle:

    initialize -> notifications/initialized -> tools/list -> tools/call

Tools:
    check_text
        text    German text to check (required)
        strict  optional boolean; warnings also fail when true
    fix_text
        text    German text to fix (required)
    format_number
        value   a number (required)
    format_money
        value     a number (required)
        currency  EUR | USD | GBP | CHF, ... (default EUR)
    format_date
        value   a date, YYYY-MM-DD or DD.MM.YYYY (required)
        long    optional boolean; long form "20. November 2026"

check_text / fix_text run skills/german-format-check/scripts/
german_format_check.py as a subprocess with --json and return the
findings. Exit-code semantics are preserved in the returned text
(0 = clean, 1 = errors found, 2 = usage error).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "skills" / "german-format-check" / "scripts" \
    / "german_format_check.py"

SERVER_INFO = {"name": "german-format-check", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"

CHECKS = """German formatting checks (GFC-01..GFC-15):
GFC-01 decimal  — English decimal point: 29.99 -> 29,99.
GFC-02 thousands — English thousands comma: 1,234 -> 1.234.
GFC-03 currency — symbol before the amount: EUR 29.99 -> 29,99 €.
GFC-04 US date  — 11/20/2026 or November 20, 2026 -> 20.11.2026.
GFC-05 12h time — 2:30 PM -> 14:30 Uhr.
GFC-06 percent  — 19% -> 19 % (warning, DIN 5008).
GFC-07 phone    — (030) 123-4567 -> 030 1234567.
GFC-08 postal   — D-10115 -> 10115; "Berlin, 10115" -> "10115 Berlin".
GFC-09 ASCII    — Muenchen -> München (warning; ASCII contexts exist).
GFC-10 months   — January -> Januar (November/December/August/
  September/April are spelled the same and are never flagged).
GFC-11 ordinal  — 1st -> 1.
GFC-12 quotes   — "..." -> „..." (warning; paired quotes only).
GFC-13 unit     — 20°C -> 20 °C.
GFC-14 VAT      — VAT -> USt. (warning).
GFC-15 day+dot  — 20 November 2026 -> 20. November 2026.
Not flagged: ISO dates (2026-11-20), German dates (20.11.2026),
German numbers (1.234,56). Formatters: numbers (1.234,56), money
(29,99 €), dates (20.11.2026 / 20. November 2026), phones
(+49 30 12345678)."""


def _run_cli(args, input_text=None, timeout=120):
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        input=input_text, capture_output=True, text=True, timeout=timeout)
    return proc


def run_check(args):
    text = args.get("text")
    if text is None:
        raise ValueError("check_text requires 'text'")
    cmd = ["check", "--json", "-"]
    if args.get("strict"):
        cmd.append("--strict")
    proc = _run_cli(cmd, input_text=str(text))
    try:
        res = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        res = {}
    lines = ["check exit code: %d" % proc.returncode]
    if res:
        for f in res.get("findings", []):
            lines.append("%s [%s] (%d-%d): %s"
                         % (f["code"], f["severity"], f["start"], f["end"],
                            f["message"]))
        lines.append("%d error(s), %d warning(s)."
                     % (res.get("errors", 0), res.get("warnings", 0)))
    if proc.stderr.strip():
        lines.append("stderr: %s" % proc.stderr.strip())
    return "\n".join(lines)


def run_fix(args):
    text = args.get("text")
    if text is None:
        raise ValueError("fix_text requires 'text'")
    proc = _run_cli(["fix", "-"], input_text=str(text))
    if proc.returncode != 0:
        return "fix failed: %s" % (proc.stderr.strip()
                                   or proc.stdout.strip())
    return proc.stdout


def run_format_number(args):
    if args.get("value") is None:
        raise ValueError("format_number requires 'value'")
    proc = _run_cli(["format-number", str(args["value"])])
    if proc.returncode != 0:
        return "format failed: %s" % (proc.stderr.strip()
                                      or proc.stdout.strip())
    return proc.stdout.strip()


def run_format_money(args):
    if args.get("value") is None:
        raise ValueError("format_money requires 'value'")
    cmd = ["format-money", str(args["value"])]
    if args.get("currency"):
        cmd.append(str(args["currency"]))
    proc = _run_cli(cmd)
    if proc.returncode != 0:
        return "format failed: %s" % (proc.stderr.strip()
                                      or proc.stdout.strip())
    return proc.stdout.strip()


def run_format_date(args):
    if args.get("value") is None:
        raise ValueError("format_date requires 'value'")
    cmd = ["format-date", str(args["value"])]
    if args.get("long"):
        cmd.append("--long")
    proc = _run_cli(cmd)
    if proc.returncode != 0:
        return "format failed: %s" % (proc.stderr.strip()
                                      or proc.stdout.strip())
    return proc.stdout.strip()


def run_list_checks(_args):
    return CHECKS


TOOLS = [
    {
        "name": "check_text",
        "description": (
            "Check German text for English-style formatting: English "
            "decimals (29.99), US dates (11/20/2026), 12-hour times "
            "(2:30 PM), currency before the amount (EUR 29.99), "
            "ASCII umlaut substitutes (Muenchen), English month names "
            "(January), straight quotes, missing spaces before units "
            "(20°C), and 10 more rules (GFC-01..GFC-15). Returns each "
            "finding with its code, position and suggested fix. ISO "
            "dates (2026-11-20) and German numbers (1.234,56) are "
            "never flagged."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "description": "The German text to check."},
                "strict": {"type": "boolean",
                           "description": "Warnings also fail when true."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "fix_text",
        "description": (
            "Fix English-style formatting in German text automatically "
            "and return the corrected text (same 15 GFC rules; fixes "
            "are applied and re-checked until the text is clean)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "description": "The German text to fix."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "format_number",
        "description": (
            "Format a number the German way: 1234.56 -> \"1.234,56\" "
            "(dot thousands separator, comma decimal separator)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {"type": "string",
                          "description": "The number to format."},
            },
            "required": ["value"],
        },
    },
    {
        "name": "format_money",
        "description": (
            "Format money the German way: 29.99 EUR -> \"29,99 €\" "
            "(two decimals, currency symbol after the amount)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {"type": "string",
                          "description": "The amount to format."},
                "currency": {"type": "string",
                             "description": "EUR (default), USD, GBP, "
                                            "CHF, or another code."},
            },
            "required": ["value"],
        },
    },
    {
        "name": "format_date",
        "description": (
            "Format a date the German way: 2026-11-20 -> "
            "\"20.11.2026\", or \"20. November 2026\" with long=true."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {"type": "string",
                          "description": "The date (YYYY-MM-DD or "
                                         "DD.MM.YYYY)."},
                "long": {"type": "boolean",
                         "description": "Long form with the month name."},
            },
            "required": ["value"],
        },
    },
    {
        "name": "list_german_format_checks",
        "description": (
            "List what this skill checks: the fifteen GFC codes, the "
            "rule behind each one, and the formatters. Call first when "
            "unsure which check applies."),
        "inputSchema": {"type": "object", "properties": {}},
    },
]

_DISPATCH = {
    "check_text": run_check,
    "fix_text": run_fix,
    "format_number": run_format_number,
    "format_money": run_format_money,
    "format_date": run_format_date,
    "list_german_format_checks": run_list_checks,
}


def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle(msg):
    method = msg.get("method", "")
    msg_id = msg.get("id")
    if method == "initialize":
        _send({"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }})
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        _send({"jsonrpc": "2.0", "id": msg_id,
               "result": {"tools": TOOLS}})
    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        try:
            fn = _DISPATCH[name]
        except KeyError:
            _send({"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32602, "message": "unknown tool: %s" % name}})
            return
        try:
            text = fn(args)
        except (ValueError, subprocess.SubprocessError) as exc:
            _send({"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32602, "message": str(exc)}})
            return
        _send({"jsonrpc": "2.0", "id": msg_id, "result": {
            "content": [{"type": "text", "text": text}]}})
    else:
        _send({"jsonrpc": "2.0", "id": msg_id, "error": {
            "code": -32601, "message": "method not found: %s" % method}})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        _handle(msg)


if __name__ == "__main__":
    main()
