# Cursor / Windsurf / Cline / Continue

The same skill, packaged for editors and agents other than Claude.

## Cursor

Copy `german-format-check.mdc` into your project's
`.cursor/rules/`:

```bash
cp cursor/german-format-check.mdc .cursor/rules/
```

The rule triggers on `*.{py,js,ts,tsx,md,mdx,txt,html,csv,json}`
whenever German text is written or reviewed. The checker script
lives in `skills/german-format-check/scripts/` — keep the `skills/`
directory in the repo (or copy the script next to the rule and
adjust the path in the rule).

## Windsurf

Copy `german-format-check.mdc` into `.windsurf/rules/`.
Windsurf reads the same `.mdc` frontmatter (`description`,
`globs`, `alwaysApply`).

## Cline

Copy the contents of `german-format-check.mdc` (minus the
frontmatter) into a `.clinerules/` file, or add the skill
directory to your workspace and point Cline at
`skills/german-format-check/SKILL.md` as a rule file.

## Continue

Add the skill as a context provider: reference
`skills/german-format-check/SKILL.md` in `.continue/rules/`
(or paste its contract section into a `rules` block in
`config.yaml`).

## The checker, anywhere

No install, no dependencies (Python 3.9+ stdlib only):

```bash
python3 skills/german-format-check/scripts/german_format_check.py check text-de.txt
python3 skills/german-format-check/scripts/german_format_check.py fix text-de.txt
```

## MCP (any client)

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

Tools: `check_text`, `fix_text`, `format_number`, `format_money`,
`format_date`, `list_german_format_checks`.
