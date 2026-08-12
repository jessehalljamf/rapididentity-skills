# jamf-identity-plugins — RapidIdentity Claude Skills

A Claude plugin **marketplace** for RapidIdentity work, containing three plugins (one skill
each):

| Plugin | Domain | Triggers on |
|---|---|---|
| `connect-action-sets` | Connect action set XML | Connect XML, `.dssproject`, action sets, suppressTrace, argDefs, scheduled jobs, CSV builds |
| `rapididentity-workflows` | Portal workflows, entitlements, Requests module | workflow JSON, `%{}` variables, advancedDssAction, valuePairs, approvals, entitlement creation |
| `generate-mr` | IDHub MR Language (Mapping Rule DSL) | `.mr` files, mapping/ingestion/policy/publication rules, PVP log triage |

The skills are kept as separate plugins deliberately: each has its own trigger vocabulary and
loads only when relevant; cross-domain tasks trigger multiple skills together, and they
cross-reference each other. (This repo began as the `connect-action-sets` skill only — the
workflows and MR skills were consolidated in from their original standalone repos on
2026-07-28.)

## Related tooling

These skills pair with [`mcp-rapidid`](https://github.com/Jamf-Concepts/mcp-rapidid), a separate
Jamf-Concepts MCP server for live-tenant RapidIdentity operations (user search, entitlements,
groups, audit logs). It's a standalone MCP server, not a plugin in this marketplace — install it
per its own README.

## Install

### Claude Code (recommended)

```bash
claude plugin marketplace add jessehalljamf/rapididentity-skills
```

Then install any or all of: `connect-action-sets`, `rapididentity-workflows`, `generate-mr`
(via `/plugin` or `claude plugin install <name>@jamf-identity-plugins`).

Skills are namespaced by plugin: `/connect-action-sets:connect-action-sets`,
`/rapididentity-workflows:rapididentity-workflows`, `/generate-mr:generate-mr`. Model
auto-triggering from skill descriptions is unaffected by namespacing.

For local testing: `claude --plugin-dir ./plugins/<plugin-name>`.

### Claude Desktop / Cowork

Upload the per-plugin bundles: [`connect-action-sets.plugin`](./connect-action-sets.plugin),
[`rapididentity-workflows.plugin`](./rapididentity-workflows.plugin),
[`generate-mr.plugin`](./generate-mr.plugin).

There is no slash-command invocation in Desktop/Cowork — that syntax is Claude Code-only. Skills
here auto-trigger purely from matching the skill's description against your request; just
describe the task naturally (e.g. mention Connect XML or a `.dssproject` file) and Claude loads
the relevant skill on its own.

### Claude.ai chat (per-skill upload)

Chat installs skills individually: [`connect-action-sets.skill`](./connect-action-sets.skill),
[`rapididentity-workflows.skill`](./rapididentity-workflows.skill),
[`generate-mr.skill`](./generate-mr.skill).

Same as Desktop — no manual invocation syntax; skills auto-trigger from the description match.

## Repo layout

```
.claude-plugin/marketplace.json        # the marketplace manifest
plugins/
├── connect-action-sets/
│   ├── .claude-plugin/plugin.json
│   └── skills/connect-action-sets/    # SKILL.md + 13 references
├── rapididentity-workflows/
│   ├── .claude-plugin/plugin.json
│   └── skills/rapididentity-workflows/  # SKILL.md + live-capture reference
└── generate-mr/
    ├── .claude-plugin/plugin.json
    └── skills/generate-mr/            # SKILL.md + 3 references
scripts/build.ps1                      # regenerates the root-level .skill/.plugin artifacts
archive/                               # untracked pre-plugin skill snapshots
TODO.md                                # skill-correction queue (see header for workflow)
```

## Notable references inside the skills

| Need | Location |
|------|----------|
| XML format rules, escaping, root element | `connect-action-sets` SKILL.md § XML Format Rules |
| Full builtin-action catalogue (grep it, never load whole) | `connect-action-sets` `references/connect-builtin-actions.json` |
| Task → builtin → verified call lookup | `connect-action-sets` `references/native-action-cheatsheet.md` |
| Connection patterns by target system | `connect-action-sets` `references/connections.md` |
| Workflow JSON ground truth (live tenant capture) | `rapididentity-workflows` `references/live-capture-request-sponsored-account.md` |
| MR Language patterns and builtins | `generate-mr` `references/patterns.md`, `references/builtins.md` |
| PVP log triage (logs can exceed 1GB — never read whole) | `generate-mr` `references/debugging-pvp-logs.md` |
