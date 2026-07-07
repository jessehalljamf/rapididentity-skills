# RapidIdentity Connect — MCP Workflow, JSON Object Model & XML ↔ JSON Conversion

Read this when working against a live Connect instance via the `RapidIdentity MCP Server:*`
tools, or when converting action sets between XML (file mode) and JSON (API model).

## Contents
- MCP Workflow — read/explore, design, push, delete
- Editing Existing Action Sets via MCP — canonical-body method, the 400/500 failures, fallback
- JSON Object Model — file JSON vs API JSON, argDef/action/arg shapes
- XML ↔ JSON Conversion — field-by-field mapping in both directions
- JSON Builtins (parseJSON / toJSON) - native values, key ordering, malformed handling, json() globals
- MCP Authoring Hazards - nested-if hoist bug, save/run timeouts, run-only-saved

---

## MCP Workflow

Use these operations when in API mode (`RapidIdentity MCP Server:*` tools available).

### Read / Explore

1. `get-connect-projects` — discover available projects
2. `get-connect-actions(project, metaDataOnly: true)` — list action sets in a project without
   pulling full content; pass an empty string for `project` to search all projects
3. `get-connect-action(id, metaDataOnly: false)` — fetch a single action set in full for
   reading or editing; `id` accepts a UUID or `project.name` format
4. `get-connect-actions(project: "$builtin", metaDataOnly: false)` — fetch the full catalog of
   platform built-in actions; load this before designing any new action set to know what
   actions are available to use
5. When the user names an action set without specifying a project, call
   `get-connect-actions` across all projects first to locate it before fetching

### Design (new from scratch)

The JSON object model below documents the wire shapes Connect uses for sections and nested actions.
Critical rules:

**Sections exist in the model and can be nested to any depth.** A section's `args` contains
only the fields that are set — `label` and `suppressTrace` are each optional, `do` is required.
Always include `label` and `suppressTrace: "true"` on every section you author. Sections without
them are valid but are an anti-pattern (they lose trace suppression and become unlabelled in the UI).

**Nesting args (`do`/`then`/`else`) must NOT have a `value` field.** The presence of `"value"`
(even `""`) tells Connect the arg is a scalar — it ignores `"actions"` and stores an empty body,
causing `Property must be a list of actions 'section.do'` (or `if.then`, `forEach.do`, etc.).
Use only `{"name": "do", "actions": [...]}` — no `value` key at all.

**Every `if` must have both `then` and `else`.** Always include both args. Empty `else` is a bare object: `{"name": "else"}` — no `value`, no `actions`. Omitting `else` entirely causes a compile error.

**`while` has only `condition` + `do` — no `else`.**
```json
{"id": "...", "name": "while", "args": [
  {"name": "condition", "value": "count < 5"},
  {"name": "do", "actions": [...]}
]}
```

**Disabled actions** use `"disabled": true` on the action object. This is the only case where `disabled` appears in the wire format — enabled actions omit it entirely:
```json
{"id": "...", "name": "log", "disabled": true, "args": [...]}
```

**Workflow for new action sets:**
1. Author the full action set JSON with sections intact, full nested logic, and nesting args
   using only `name` + `actions` (never `value`)
2. Push via `save-connect-action`
3. Run to verify — if a compile error names `section.do` or `if.then`, a nesting arg has a
   spurious `value` field

Follow all existing naming conventions, section order, argDef rules, and logging conventions
from this skill when designing the structure.

### Push (create or update metadata)

- Use `save-connect-action` to create or update the full action set including nested action logic
- On **update**: always use the `version` number returned from the most recent
  `get-connect-action` call — never assume or hardcode the version number
- If a version conflict error is returned, re-fetch the action set to get the current version
  before retrying

### Delete

- Use `delete-connect-action(id)`
- **Always confirm with the user before executing** — deletion is irreversible

---

## Editing Existing Action Sets via MCP

Guidance for **editing an existing** action set via `save-connect-action`. (The
Design (new from scratch) workflow above covers authoring new ones.) The headline rule
prevents the most common and most time-wasting failure mode.

### Build the save by minimally mutating the fetched canonical body

**Always construct an update by taking the exact object returned by
`get-connect-action(metaDataOnly: false)` and changing only the few nodes you need. Never
rebuild a large body from fragments.** Re-assembling a large action set by hand is what
introduces malformed fields; mutating the server's own canonical object in place avoids them.

The MCP save handles large bodies without trouble — a full ~330-node, ~80 KB action set saves
cleanly when the body is the canonical fetch plus a minimal edit. There is no size or
complexity ceiling that forces you off the MCP save path for a normal edit.

Procedure:
1. `get-connect-action(id, metaDataOnly: false)` → capture `version` and the full body.
2. Mutate that object minimally and in place — change only the intended nodes.
3. `save-connect-action` with the `version` from step 1 (see Push above).

### The `400 "The field name is invalid"` — read it literally

```
{"success": false, "message": "The field name is invalid", "httpStatus": 400}
```

This message is **literal**: an `arg`'s `name` (a "field name") somewhere in the body you
submitted is malformed — empty, wrong, or structurally misplaced (e.g. a nesting arg given a
spurious `value`; see § Arg shapes). It is **not** an opaque server-side content validator and
**not** an escaping artifact. It is almost always a defect in a hand-assembled body.

**Diagnose it with a canonical round-trip:** fetch the body, change one trivial thing, save.
That succeeds — proving the endpoint accepts the content and isolating the fault to *your diff*.
Then diff your intended body against the canonical fetch to find the bad `name`. Compare the two
objects; don't theorize about the server.

### The `500 ConstraintViolationException` — node-id uniqueness is *per action set*

```
javax.persistence...ConstraintViolationException: could not execute statement   (httpStatus 500)
```

A real, **separate** failure from the 400: a DB uniqueness violation. But the scope is **per
action set, not global**. Connect keys action-node `id`s by their parent action set — the
effective unique key is *(action-set identity + node `id`)*. Two different action sets can
hold the **same** node `id`s with no collision.

**Proven empirically:** an API clone of `Tools_RICloudUserDetail` → `Tools_RICloudUserDetail_copy`
kept all 51 node `id`s byte-identical; both sets coexist and run on the same live instance.
Only the action-set `name` changed.

So:

- **Cloning a whole action set** (API clone, or export→rename→import) does **not** require
  re-IDing nodes — the new name/identity disambiguates. Do not re-ID whole-set clones.
- The only hard constraint is **no duplicate node `id` within a single set's body**.
- **Copying a section into a *different* existing set** may keep the source `id`s — *unless*
  the destination already contains those exact `id`s (a within-body duplicate).
- A throwaway probe just needs its **own** action-set identity and no duplicate `id`s within
  its body; it may reuse another set's node `id`s.

The 500 therefore signals a **within-body duplicate `id`** (a section pasted into a set that
already held those `id`s, or a probe reusing a real set's action-set identity), not a
cross-set collision.

### What the save endpoint demonstrably ACCEPTS

A canonical body containing all of the following round-trips cleanly, so none of these ever
causes the 400 — if you see one, suspect your diff:

- `argDefs` with `optional: true` and `type` like `enum:debug,normal,quiet`.
- `setRecordFieldValue` / `setRecordFieldValues` whose `field` arg is a non-literal
  expression/variable (`groupUIDAttr`, `pair.id`, `riMemberRecord[userUIDAttr]`,
  `riGroupRecord['@dn']`).
- Non-UUID-format action-node `id`s (e.g. `CG-0003-SEC-...`, `MSF-OBS-...`).
- Raw `&&`, `<`, `>` written literally in `value` strings (the serializer returns them as
  `\u0026`/`\u003c`/`\u003e`; sending raw is equivalent — see XML ↔ JSON Conversion below).
- Echoing back the server-managed metadata fields; the server overwrites them.

### Throwaway-probe technique (safe interrogation)

To test what the save accepts **without touching a production action set**: create a **new**
action set with its **own** fresh action-set identity, a `zz`-prefixed name (e.g. `zzProbeDeleteMe`),
`version: 0`, and **no duplicate node `id`s within its body** (it may reuse another set's node
`id`s — uniqueness is per-set, so it need not re-ID everything); save; observe;
`delete-connect-action`. A probe `500` (within-body duplicate `id`) tells you nothing about a
`400` (malformed field) — different failure classes. Confirm no `zz...` row persists afterward.

### XML-import fallback (genuine, but not the default)

The Connect UI's XML import is more permissive than a hand-built JSON save, and is a legitimate
fallback **only** when you genuinely cannot produce a clean JSON body — not a reflex when a 400
appears (the 400 is a fixable defect in your own body). If used: edit the standalone
`<actionDefs>` XML, have the user import it through the UI, then re-fetch and verify. Two side
effects to know: the import **carries the file's `modifiedBy`/`modifiedByName`** (the audit trail
may show the original author, not the importer), and the importer **may rewrite some node `id`s** —
re-fetch to capture canonical IDs.

### Stamping behavior (refines the server-managed fields under API JSON above)

- `version` is the reliable per-action-set monotonic edit counter (e.g. 9 → 10 on one save). Use
  it for "has this changed" and for the save `version` field.
- `changeCount` is **not** a per-action-set edit count — it behaves as an instance-wide monotonic
  sequence (one save moved it 9514 → 9516; an unrelated UI import moved it 8161 → 9514). Don't read
  it as one set's edit history; use `version`.
- `modifiedBy` / `modifiedByName` vary by path: an MCP save stamps the calling MCP identity
  (observed once as a bare id with an empty `modifiedByName`); a UI XML import carries the file's
  own values. Don't rely on these to identify who changed something.

### Post-edit verification checklist (after any edit — MCP or UI import)

Re-fetch and confirm: `version` incremented by exactly 1; each new node `id` present exactly
once; any structural counter moved by the expected amount; a char-level diff shows only the
intended regions changed; untouched metadata intact; no new non-ASCII in editor-facing strings
(comments, `description`, labels stay plain ASCII; pre-existing non-ASCII elsewhere is fine to
leave).

---

## JSON Object Model

### File JSON (downloaded from Connect UI)

The minimal format Connect exports when downloading an action set as JSON. Contains only:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Action set name — same naming rules as XML |
| `project` | string | Project name; empty string for the `<Main>` project |
| `category` | string | Usually empty string |
| `description` | string | Same description template as XML |
| `returnsValue` | boolean | `true` for `Fn*` functions; `false` for jobs/utilities |
| `builtIn` | boolean | Always `false` for user-defined action sets |
| `community` | boolean | Always `false` for user-defined action sets |
| `argDefs` | array | See argDef shape below |
| `actions` | array | See action shape below |

### API JSON (used with `save-connect-action` / returned by `get-connect-action`)

All file JSON fields plus these API/server fields:

| Field | Type | Value on create | Notes |
|---|---|---|---|
| `id` | UUID string | Generate new UUID v4 | Required |
| `version` | integer | `0` | Must match server value on update |
| `sensitive` | boolean | `false` | `true` only if the action set handles credentials |
| `unlicensed` | boolean | `false` | Always `false` |
| `deprecated` | string | `""` | Empty string if not deprecated |
| `changeCount` | integer | `0` | Server manages on update |
| `modifiedMs` | integer | `0` | Server manages on update |
| `modifiedBy` | string | `""` | Server manages on update |
| `modifiedByName` | string | `""` | Server manages on update |
| `httpStatus` | integer | `0` | Server field |

### argDef shape

File JSON omits fields that are absent; API JSON must include all fields.

| Field | Type | Notes |
|---|---|---|
| `name` | string | Parameter name |
| `type` | string | `string`, `boolean`, `number`, `object`, `array`, `enum:val1,val2,...` |
| `description` | string | Required — same rule as XML |
| `optional` | boolean | Only present when `true` |
| `value` | string | Default value; absent when none |

### Action shape

The wire format is minimal — only include fields that are set:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | Always present — generate UUID v4 per action on create |
| `name` | string | Always present — built-in action name or custom action set name |
| `outputVar` | string | Only include when non-empty |
| `disabled` | boolean | Only include when `true` (disabled action); omit entirely when `false` |
| `project` | string | Omit entirely — not part of the native wire format |
| `args` | array | Always present, even if empty (`[]`) |

### Arg shapes

There are exactly two mutually exclusive arg forms. Never mix them:

*Value arg* — any arg carrying an expression, literal, or scalar:
```json
{ "name": "condition", "value": "someExpression" }
```

*Nesting arg* — `do`, `then`, `else`, or any arg containing child actions. **No `value` field.**
```json
{ "name": "do", "actions": [ ...child action objects... ] }
```

*Bare `else`* — empty else branch with no children:
```json
{ "name": "else" }
```

The `optional`, `type`, and `description` fields are omitted on both forms in the native API
wire format. The MCP tool schema previously required them but the struct has been updated to
use `omitempty` — pass them only when they carry meaningful values.

---

## XML ↔ JSON Conversion

### XML → JSON (file/disk to API)

Use when taking a downloaded or hand-authored XML action set and pushing it to the live system
via `save-connect-action`.

**Action set wrapper:**

| XML | JSON |
|---|---|
| `<actionDef name="X" returnsValue="true" description="...">` | `name`, `returnsValue`, `description` top-level fields |
| `<argDefs><argDef name="X" type="Y" optional="true" description="Z"/>` | `argDefs` array entry; add `value: ""` for API JSON |
| Standalone `<actionDefs>` import wrapper | Discard — not part of JSON model |

**Actions and args:**

| XML | JSON |
|---|---|
| `<action name="section">` | `{ "name": "section", "args": [ {label arg}, {suppressTrace arg}, {do nesting arg} ] }` — sections are preserved as-is |
| `<action name="X" outputVar="Y">` | Action object: `name`, generated UUID `id`, `outputVar: "Y"` |
| `<action name="X">` (no outputVar) | Action object: `name`, generated UUID `id`; omit `outputVar` |
| `<arg name="do">` / `<arg name="then">` / `<arg name="else">` containing child actions | `{ "name": "do", "actions": [...child action objects...] }` — **no `value` field** |
| `<arg name="else"/>` (empty else, no child actions) | `{ "name": "else" }` — bare name only, no `value`, no `actions` |
| `<arg name="X" value="someExpr"/>` (any non-nesting arg) | `{ "name": "X", "value": "someExpr" }` |

**String escaping (XML → JSON):**

| XML attribute | JSON value |
|---|---|
| `&quot;` | `"` |
| `&amp;` | `&` |
| `&lt;` | `<` |
| `&gt;` | `>` |

**API field defaults to supply when pushing file JSON to MCP:**
- Top-level: `id` (new UUID v4), `version: 0`, `sensitive: false`, `unlicensed: false`,
  `deprecated: ""`, `changeCount: 0`, `modifiedMs: 0`, `modifiedBy: ""`,
  `modifiedByName: ""`, `httpStatus: 0`
- Each action: `disabled: false`, `project: "$builtin"` (or the project name for calls to
  custom action sets)
- Each value arg: `type: ""`, `optional: false`, `description: ""`
- Each argDef: `optional: false` if absent, `value: ""` if absent

---

### JSON → XML (API to file/disk)

Use when taking a live action set fetched via `get-connect-action` and saving it as a local
XML file.

**Action set wrapper:**

| JSON | XML |
|---|---|
| `name`, `returnsValue`, `description` | `<actionDef name="X" returnsValue="true/false" description="...">` |
| `argDefs` array | `<argDefs>` block with one `<argDef>` per entry; omit `optional` attribute if `false`; omit `value` attribute if empty string |
| `id`, `version`, `sensitive`, `unlicensed`, `deprecated`, `changeCount`, `modifiedMs`, `modifiedBy`, `modifiedByName`, `httpStatus` | **Omit entirely** — API metadata, no XML equivalent |

**Actions and args:**

| JSON | XML |
|---|---|
| Action object `name` + non-empty `outputVar` | `<action name="X" outputVar="Y">` |
| Action object `name` + empty `outputVar` | `<action name="X">` — omit the attribute |
| `disabled`, `project` on action object | **Omit** — API-only fields |
| `{ "name": "do", "actions": [...] }` (file JSON nesting arg) | `<arg name="do">` containing child `<action>` elements (recurse for nested nesting args) |
| `{ "name": "do", "value": "", "actions": [...] }` (API nesting arg) | `<arg name="do">` containing child `<action>` elements (recurse for nested nesting args) |
| `{ "name": "X", "value": "expr" }` (any non-nesting arg) | `<arg name="X" value="expr"/>` |

**String escaping (JSON → XML):**

| JSON value | XML attribute |
|---|---|
| `"` | `&quot;` |
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |

**Output format:** Apply all standard XML format rules from § XML Format Rules — no `<?xml`
declaration, no indentation, single-line compact output, all sections with
`suppressTrace="true"`.

---

## JSON Builtins — parseJSON / toJSON (object model)

`parseJSON(json)` and `toJSON(item, indent?)` are built-in **actions** (each takes an `outputVar`).
`toJSON` is also callable inline as an expression function (e.g. the httpPOST body). They live in
the platform `json-actions.js` and are the preferred replacements for `JSON.parse` / `JSON.stringify`.

- **`parseJSON` returns native JS values** - objects (dot/bracket/nested access), real arrays
  (`Array.isArray` true; `.length`, indexing, `.map`, arithmetic), top-level scalars
  (`parseJSON('42')` -> number), `null`, and preserved unicode. Seed an empty object with
  `parseJSON('{}')`.
- **Malformed input does not abort** - `parseJSON` auto-logs its own ERROR (json-actions.js) and
  returns `undefined`. Pre-gate with an `isValidJSON` (try/catch around native `JSON.parse`) guard
  when you need clean branching without the noisy auto-error.
- **`toJSON` is the type-agnostic serializer** - `toJSON(item)` compact, `toJSON(item, true)`
  4-space indented. Handles plain objects, accumulated objects, and `createRecord` Records. (The old
  `JSON.stringify` StackOverflow warning is type-specific to live Java-wrapped objects.)
- **Key ordering** - `createRecord` Records serialise alphabetically (TreeMap-like); plain and
  `parseJSON`-seeded objects keep insertion order. Numbers normalise (`1234`, not `1234.0`).
- **Record-concat gotcha** - `"" + record` yields a Java map `toString`
  (`{employeeNumber=1234.0, ...}`), not JSON. Use `toJSON(record)`.
- **`json()`-wrapped SharedGlobals are pre-parsed** - `Global.<key>` for a `json([...])` /
  `json({...})` value is already a native array/object; never `parseJSON` / `JSON.parse` it (that
  stringifies then throws `SyntaxError`). Parsing is only for raw JSON strings (HTTP bodies, file
  reads, string-typed args).

---

## MCP Authoring Hazards (observed on jar 2026.05.0)

### Trailing siblings after a mid-block nested `if` are hoisted (compile break)

When a `then` / `else` / `do` actions array contains a nested `if` (or `while`) that is **not the
last element**, the `save-connect-action` round-trip hoists the actions that follow it up onto the
parent `if` as bare `{"name":"<action>"}` stubs (no `args`, no `id`). The set then fails to compile:

```
java.lang.IllegalArgumentException: Error compiling action set 'X': Can't redefine property 'if.setRecordFieldValue'
    at net.idauto.exodus.dss.ActionCompiler.getCoreArgs
    at net.idauto.exodus.dss.ActionCompiler.compileIf
```

Workarounds (any one):
1. Make the nested `if` / `while` the **last** element of its container.
2. Replace mid-block branching with flat ternary `setVariable` expressions (parseJSON gives native
   values, so type/shape decisions collapse into ternaries).
3. Push the post-branch logic **into** each branch so nothing trails the nested control-flow action.

Detection (Python, before saving): walk every `then` / `else` / `do` actions array and assert no
element of `name` `if` / `while` appears at an index other than the last.

### A client timeout does not mean the save failed

`save-connect-action` / `run-connect-action` can hang the MCP client (multi-minute timeout) while
the server keeps working; the write may still commit. **Always re-fetch and confirm the `version`
incremented** before re-saving. Never blind-retry a save (risks node-id collisions / duplicates).

### Run only saved action sets

Running a bare, unsaved `section` / action inline via `run-connect-action` throws
`NullPointerException` in `ActionCompiler.compileActionDef`. Save the action set first, then run it
by name (`{name, project, id, args}`).
