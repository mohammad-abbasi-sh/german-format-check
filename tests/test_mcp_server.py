"""End-to-end tests for the german-format-check MCP server over stdio.

Spawns mcp-server/german_format_check_mcp_server.py, runs the MCP
lifecycle (initialize -> tools/list -> tools/call), and checks the
tools return real findings. Run: python3 -m pytest tests/ -q
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = (HERE.parent / "mcp-server"
          / "german_format_check_mcp_server.py")


def _session(calls):
    """Send a list of JSON-RPC messages, return the parsed responses."""
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    payload = "".join(json.dumps(c, ensure_ascii=False) + "\n"
                      for c in calls)
    out, _ = proc.communicate(payload, timeout=120)
    assert proc.returncode == 0
    return [json.loads(line) for line in out.strip().splitlines()
            if line.strip()]


def _initialize():
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05",
                    "capabilities": {}, "clientInfo": {"name": "test",
                                                       "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]


def _call(msg_id, name, args):
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
            "params": {"name": name, "arguments": args}}


def _text(resp):
    assert "error" not in resp, resp
    return resp["result"]["content"][0]["text"]


def test_initialize_and_tools_list():
    resps = _session(_initialize() + [
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    init = resps[0]
    assert init["result"]["serverInfo"]["name"] == "german-format-check"
    assert init["result"]["protocolVersion"] == "2024-11-05"
    names = [t["name"] for t in resps[1]["result"]["tools"]]
    assert names == ["check_text", "fix_text", "format_number",
                     "format_money", "format_date",
                     "list_german_format_checks"]


def test_check_text_finds_errors():
    resps = _session(_initialize() + [
        _call(2, "check_text",
              {"text": "Der Preis ist €29.99 am November 20, 2026."})])
    text = _text(resps[1])
    assert "GFC-03" in text
    assert "GFC-04" in text
    assert "check exit code: 1" in text
    assert "2 error(s)" in text


def test_check_text_clean():
    resps = _session(_initialize() + [
        _call(2, "check_text", {"text": "Der Preis ist 29,99 €."})])
    text = _text(resps[1])
    assert "check exit code: 0" in text
    assert "0 error(s), 0 warning(s)" in text


def test_fix_text_round_trip():
    resps = _session(_initialize() + [
        _call(2, "fix_text",
              {"text": "Der Preis ist €29.99 in Muenchen."})])
    assert _text(resps[1]).strip() == "Der Preis ist 29,99 € in München."


def test_format_number_tool():
    resps = _session(_initialize() + [
        _call(2, "format_number", {"value": "1234.56"})])
    assert _text(resps[1]) == "1.234,56"


def test_format_money_tool():
    resps = _session(_initialize() + [
        _call(2, "format_money", {"value": "29.99", "currency": "EUR"})])
    assert _text(resps[1]) == "29,99 €"


def test_format_date_tool_short_and_long():
    resps = _session(_initialize() + [
        _call(2, "format_date", {"value": "2026-11-20"}),
        _call(3, "format_date", {"value": "2026-11-20", "long": True})])
    assert _text(resps[1]) == "20.11.2026"
    assert _text(resps[2]) == "20. November 2026"


def test_list_checks_tool():
    resps = _session(_initialize() + [
        _call(2, "list_german_format_checks", {})])
    text = _text(resps[1])
    for code in ("GFC-01", "GFC-04", "GFC-09", "GFC-15"):
        assert code in text


def test_unknown_tool_returns_error():
    resps = _session(_initialize() + [_call(2, "no_such_tool", {})])
    assert resps[1]["error"]["code"] == -32602


def test_missing_argument_returns_error():
    resps = _session(_initialize() + [_call(2, "check_text", {})])
    assert resps[1]["error"]["code"] == -32602
