# Connect Action Sets — Claude Skill

A Claude Code skill for authoring, reviewing, and refactoring **RapidIdentity Connect** action sets in XML.

## Installation

1. Download [`connect-action-sets.skill`](./connect-action-sets.skill)
2. Place it in your Claude Code skills directory (typically `~/.claude/skills/`)
3. The skill activates automatically when you work with Connect XML, `.dssproject` files, or ask Claude about RapidIdentity Connect

## What It Does

Triggers when you:
- Create, edit, or refactor Connect action sets (XML)
- Ask about naming conventions, section structure, logging, counters, or argDefs
- Reference a `.dssproject` file or paste Connect XML
- Work against a live Connect instance via the RapidIdentity MCP server (API mode)

## Contents

```
connect-action-sets/
├── SKILL.md                          # Core skill — XML rules, naming, patterns, templates
└── references/
    ├── connect-builtin-actions.json  # Full catalogue of built-in Connect actions
    ├── connections.md                # Typed connection patterns (AD, Google, M365, LDAP, etc.)
    ├── mcp-and-json.md               # MCP workflow, JSON object model, XML ↔ JSON conversion
    ├── openldap-schema.md            # OpenLDAP / ID Store attribute reference
    ├── oracle-fusion-hcm-api.md      # Oracle Fusion HCM — auth, Workers API, pagination
    ├── ri-alternate-actions.md       # Alternate Action input/output contracts
    ├── ri-connect-admin-api.md       # Connect admin REST API — trigger jobs, processes, files
    ├── ri-sponsorship-api.md         # RapidIdentity Sponsorship API
    ├── ri-workflow-variables.md      # Workflow variable substitution and WFM return contract
    ├── shared-globals.md             # Standard SharedGlobals keys by category
    └── skyward-qmlativ-api.md        # Skyward Qmlativ — auth, Custom API patterns
```

## Quick Reference

| Need | Location |
|------|----------|
| XML format rules, escaping, root element | `SKILL.md` § XML Format Rules |
| Naming conventions and prefixes | `SKILL.md` § Naming Scheme |
| Logging and counting patterns | `SKILL.md` § Logging / § Counting |
| Full action set skeleton | `SKILL.md` § Skeleton Templates |
| Validation checklist | `SKILL.md` § Validation Checklist |
| Connection patterns by target system | `references/connections.md` |
| All built-in actions | `references/connect-builtin-actions.json` |
| MCP / live Connect workflow | `references/mcp-and-json.md` |
