---
name: generate-mr
description: >
  Generate, write, and edit IDHub MR Language (Mapping Rule DSL) code for the IDHub
  Provisioning Pipeline (PVP). Trigger this skill whenever the user says "generate MR",
  "write MR", "create MR", "write a mapping rule", "generate a mapping rule", "write an
  ingestion rule", "write a policy rule", "write a publication rule", or anything that
  asks Claude to produce .mr file content. Also trigger when the user describes a
  mapping scenario (e.g., "map OneRoster fields to IDHub attributes", "assign AD OU
  based on employee type", "generate a username policy", "write a correlation rule")
  even if they don't use the phrase "MR". If the user shows existing MR code and wants
  it modified, reviewed, or explained, use this skill. Also trigger when the user asks why
  a PVP/pipeline run had failures or asks to examine a `pvp.log` file — see
  `references/debugging-pvp-logs.md` for the log-triage recipe (these logs can exceed 1GB
  and must never be read in full).
---

# IDHub MR Language — Code Generation Guide

You are generating MR Language code for the IDHub Provisioning Pipeline. MR is a declarative DSL — no loops, no user-defined functions, no side effects. Every file maps source fields to target attributes using `let` statements.

## Quick Reference: File Structure

Every MR file has this shape:

```
ruleID = <uuid-or-adapter-guid>
ruleType = person   // or: group

// Optional comment describing the rule

let <targetAttribute> = <expression>
let <targetAttribute> = <expression>
...
```

- `ruleID` is a UUID. Generate a plausible UUID if the user doesn't provide one.
- `ruleType` is almost always `person`; use `group` only when the rule operates on group records.
- Blank lines and `//` comments are allowed anywhere after the header.
- Pseudo-attributes are prefixed with `@` (e.g., `@ou`, `@activationOffset`).

---

## Expression Types

### 1. Direct Assignment
```
let givenName = firstName
let idautoPersonStuID = sourcedId
```

### 2. String Concatenation (`+`)
```
let displayName = givenName + " " + sn
let mail = idautoPersonUserNameMV + "@district.edu"
```
Null in any operand makes the whole expression null — guard with `if` if a field may be absent.

### 3. `when` — Multi-branch conditional
```
let employeeType = when {
    roles.contains("student") -> "student"
    roles.containsAny("teacher", "staff") -> "staff"
    else -> ""
}
```
Branches evaluated top-to-bottom; first match wins. `else` is optional. Numeric and null values are valid:
```
let @activationOffset = when {
    employeeType.contains("staff") -> 259200
    else -> -1
}
```

### 4. `if`/`else` — Two-branch conditional with null guard
```
let idautoPersonStuID = if (roles.contains("student")) id
let mail = if (email == "noreply@school.edu") givenName + "@district.edu" else email
```
**Key behavior:** If any field referenced in the `if` condition is null (absent from the source record), the entire expression returns null — the `then` and `else` branches are never evaluated. Use this to your advantage for conditional field assignment, but be aware it can suppress output unexpectedly.

### 5. Null assignment
```
let idautoPersonProfileUrl = null
```
Explicitly suppresses output for a field.

### 6. Boolean and number literals
```
let pwdReset = true
let @activationOffset = -1
```

---

## Built-in Functions — String (Single-Valued)

| Built-in | Signature | Common Use |
|---|---|---|
| `lowercase` | `field.lowercase()` | Username normalization |
| `uppercase` | `field.uppercase()` | All-caps IDs |
| `titleCase` | `field.titleCase()` | Display name normalization |
| `take` | `field.take(n)` | Safe prefix truncation |
| `takeLast` | `field.takeLast(n)` | Suffix extraction |
| `substring` | `field.substring(start[, end])` | ⚠ Throws if out of bounds — prefer `take` |
| `replace` | `field.replace("find", "replacement"[, true])` | Domain substitution, prefix removal |
| `startsWith` | `field.startsWith("prefix")` | Conditional logic |
| `endsWith` | `field.endsWith("suffix")` | Conditional logic |
| `containsText` | `field.containsText("str")` | Substring check (case-sensitive) |
| `isEmpty` | `field.isEmpty()` | Empty string guard |
| `isNotEmpty` | `field.isNotEmpty()` | Presence check |
| `length` | `field.length` | No parentheses |
| `getWord` | `field.getWord(i[, "delim"])` | Split and extract |
| `stripDiacriticals` | `field.stripDiacriticals()` | é→e, ñ→n for usernames |
| `stripSpaces` | `field.stripSpaces()` | Remove whitespace |
| `stripSpecialCharacters` | `field.stripSpecialCharacters()` | Remove non-alphanumeric |
| `stripQualifiers` | `field.stripQualifiers()` | Remove Jr., Ph.D., etc. |
| `calculateGradYear` | `field.calculateGradYear([cutoffMonth])` | Single-valued grade level |
| `convertDateFrom` | `field.convertDateFrom("pattern")` | → RI standard (yyyy-MM-dd) |
| `convertDateTo` | `field.convertDateTo("pattern")` | RI standard → output format |
| `convertDate` | `field.convertDate("inPat", "outPat")` | One-step format conversion |
| `convertDateTimeFrom` | `field.convertDateTimeFrom("pattern")` | → RI datetime standard |
| `convertDateTimeTo` | `field.convertDateTimeTo("pattern")` | RI datetime → output format |
| `convertDateTime` | `field.convertDateTime("inPat", "outPat")` | One-step datetime conversion |
| `incrementOnCollision` | `field.incrementOnCollision([maxLen[, startIdx]])` | Collision-safe usernames (policy only) |
| `similarity` | `field.similarity("other"[, precision])` | Normalized Levenshtein similarity (0.0–1.0). Rarely needed directly — fuzzy match rules (below) use this internally. |
| `round` | `field.round(decimals)` | Rounds a numeric string result (e.g. chained off `similarity`) to N decimal places. |

---

## Built-in Functions — Lists (Multi-Valued)

| Built-in | Signature | Common Use |
|---|---|---|
| `[n]` | `field[0]` | Index access (0-based) |
| `contains` | `field.contains("value")` | Exact match in list |
| `containsAny` | `field.containsAny("v1", "v2", ...)` | Any of several exact matches |
| `containsExactly` | `field.containsExactly("v1", ...)` | List has exactly these values |
| `isListEmpty` | `field.isListEmpty()` | Null-safe empty check |
| `isListNotEmpty` | `field.isListNotEmpty()` | Null-safe non-empty check |
| `listCount` | `field.listCount` | No parentheses |
| `calcGradYear` | `field.calcGradYear([cutoffMonth])` | Multi-valued grade level list |
| `mapWithSelector` | `field.mapWithSelector("subField")` | Extract sub-field from array of objects |
| `anyChildContains` | `field.anyChildContains("subField", "value")` | Exact match in array of objects |
| `anyChildContainsText` | `field.anyChildContainsText("subField", "substr")` | Substring match in array of objects |

---

## Built-in Functions — Standalone (No Field Context)

```
randomNumber(digits)    // e.g., randomNumber(4) → "8423"
randomString(length)    // e.g., randomString(64) → secure alphanumeric string
now()                   // Current datetime in LDAP Generalized Time
today()                 // Today's date as yyyy-MM-dd
```

---

## Nested Object Access

```
// Object field: source has { "demographics": { "birthday": "2004-04-12" } }
let idautoPersonBirthdate = demographics{"birthday"}

// Find in array: source has [ { "type": "HR", "identifier": "HR-12345" }, ... ]
let idautoPersonSystem1ID = user_ids.find("type", "HR"){"identifier"}
```

---

## Building Structured Output (for Sink Systems)

```
// Single object
let email = {"address": mail, "primary": true, "type": "work"}

// Array of values
let names = [idautoPersonUserNameMV, displayName]

// Array of objects
let emails = [
    {"address": mail, "primary": true, "type": "work"},
    {"address": idautoPersonHomeEmail, "primary": false, "type": "home"}
]
```

---

## Policy Pseudo-Attributes

These are used in **application** (policy) rules and control PVP's behavior:

| Pseudo-attribute | Type | Purpose |
|---|---|---|
| `@ou` | string | AD OU path for account placement |
| `@activationOffset` | integer (seconds) | Delay before activating a new account. `-1` = disabled |
| `@deactivationOffset` | integer (seconds) | Delay before deactivating an expired account. `-1` = disabled |
| `@renameOffset` | integer (seconds) | Delay before applying a username rename. `-1` = no renames, `0` = immediate |
| `@endUserRenameEmailNotification` | boolean | Send email to end user when rename is queued |
| `@managerIdentifierAttribute` | string | ID Store attribute to use for manager linkage |
| `@defaultManagerID` | string | Fallback manager ID when none is resolved |
| `@passwordPolicy` | object | Packed password + sync policy |
| `@passwordSyncPolicy` | string | `ALWAYS` \| `CHANGES_ONLY` \| `NEVER`. Only ever set **nested inside** the packed `@passwordPolicy` object below — never as a standalone top-level `let`. |
| `@publishPasswordOnUpdate` | boolean | Controls whether a password is republished to sinks on an update (not just an add). Note: Google Workspace has no NOP guard on password writes — every run where this resolves `TRUE` costs an API call regardless of whether the password actually changed. |
| `@usernameOrder` | list (policy rule) | Ordered list of candidate values IDHub tries, in order, when resolving/validating the primary username. See example below. |
| `@username` | string (interpolation token) | **Not a `let` target.** A literal token you embed inside another attribute's *string expression* in a policy rule — IDHub substitutes it with the resolved username at generation time. Used to derive dependent values (mail, extension attributes) from the username without re-deriving it. See example below. |

### `@usernameOrder` — candidate username fallback list
```
let @usernameOrder = [idautoPersonUserNameMV, mail, idautoPersonStuID]
```
IDHub tries each field in order and uses the first that resolves to a usable value.

### `@username` — username interpolation token
Use the literal string `"@username"` inside a concatenation to build attributes derived from
the resolved username, without duplicating the username-generation expression:
```
// Email derived from the resolved username, not from a separate expression
let mail = "@username" + "@district.edu"

// Extension attribute built from the resolved username
let idautoPersonExt17 = "edu/idauto/" + "@username"
```
This only works in **policy rules**, on the same pass that generates
`idautoPersonUserNameMV` — it is not a generic pseudo-attribute you set with `let @username = ...`.

### `incrementOnCollision`
Collision-safe username generation (policy rules only):
```
let idautoPersonUserNameMV = when {
    else -> (givenName.take(1).lowercase() + sn.lowercase()).incrementOnCollision(24, 1)
}
```
Arguments: `incrementOnCollision(maxBaseLength, startIndex)`. Both are optional (defaults: no truncation, start at 1). The system appends a numeric suffix if the generated username already exists.

### Packed `@passwordPolicy` object
```
let @passwordPolicy = {"userPassword": (givenName.lowercase()).take(1) + sn.uppercase() + "1", "pwdReset": false, "@passwordSyncPolicy": "CHANGES_ONLY"}
```

---

## Match Rules (Correlation Pass)

```
// Exact match — AND logic (all keys in same group must match)
let key exact a idautoPersonStuID = sourcedId
let key exact a mail = email

// OR logic (different group names)
let key exact a idautoPersonStuID = id
let key exact b idautoPersonHRID = id

// Guarded keys (conditional)
let key exact a idautoPersonStuID = if (roles.contains("student")) id
let key exact b idautoPersonHRID = if (roles.contains("student") == false) id

// Fuzzy match (⚠ last resort only — 75% Levenshtein threshold)
let key fuzzy givenName = first_name
let key fuzzy sn = last_name
```

---

## Code Generation Guidelines

### Style

1. **Always include a comment block** after the header explaining what the rule does and where it's used (ingestion from X, publication to Y, policy for Z).
2. **Comment complex `when` branches** — especially OU placement rules with many branches; a brief inline comment on non-obvious branches helps maintainers.
3. **One attribute per `let`** — never attempt to combine multiple assignments.
4. **Order `let` statements logically**: required ID fields first, then names, then classification fields, then contact info, then pseudo-attributes last.
5. **Use `when` for 3+ branches, `if` for 2 branches** — never nest `if/else` chains.
6. **Use `isListEmpty`/`isListNotEmpty` instead of `if (field)` for list fields** — the null guard in `if` won't catch an empty list.
7. **`else -> -1` is the canonical "disabled" sentinel** for numeric offset pseudo-attributes.
8. **Use `stripDiacriticals().lowercase()` before using a name in a username** — prevents provisioning failures for accented names. Note: as of IDHub 2026.04.0, generated usernames have `.stripSpaces().stripDiacriticals()` applied automatically at generation time, so these calls are no longer strictly *required* in a username-policy expression — but keep writing them explicitly anyway for readability and for any other attribute (e.g. `mail`) that reuses the same name fields outside the username-generation path, where the auto-strip does not apply.

### Choosing Built-ins

- **Username from name:** `givenName.stripDiacriticals().lowercase().take(1) + sn.stripDiacriticals().stripSpecialCharacters().lowercase()`
- **Safe truncation:** `take(n)` — never `substring` unless you're certain the field is long enough
- **Date ingestion:** `field.convertDateFrom("MM/dd/yyyy")` produces RI standard `yyyy-MM-dd`
- **Grade-based grad year (flat list):** `gradeLevel.calcGradYear()`
- **Grade-based grad year (single value):** `grade.calculateGradYear()`

### Common Gotchas to Avoid

- Null in any `+` operand makes the entire concatenation null — guard if a field may be absent.
- `isEmpty` is for strings; `isListEmpty` is for lists — using the wrong one silently returns wrong results.
- `substring(n, m)` throws if the string is shorter than `m` — prefer `take`.
- `contains` on a string field doesn't match — it only works on list fields; for strings use `containsText`.
- In `when`, always put the most-specific condition first (disabled-account checks before type-based checks, etc.).
- The `else` in a `when` is optional — omitting it means unmatched records produce null (attribute left unset).
- A pseudo-attribute name is **not validated by the grammar** — `let @activationOfset = ...` (misspelled) parses successfully and silently produces a dead no-op attribute. Double-check pseudo-attribute spelling against the table above; there is no compiler diagnostic for a typo'd `@name`.

---

## Rule Type Templates

### Ingestion Rule (Source System → ID Store)
```
ruleID = <uuid>
ruleType = person

// Ingestion: <SourceSystemName> → ID Store
// Maps <source> fields to IDHub standard attributes.

let idautoPersonSystem1ID = <sourceUniqueId>
let givenName = <firstName>
let sn = <lastName>
let idautoPersonMiddleName = <middleName>
let displayName = givenName + " " + sn
let mail = <email>
let employeeType = <roleField>
```

### Policy Rule (ID Store → Account Controls)
```
ruleID = <uuid>
ruleType = person

// Policy rule for <audience> accounts.
// Controls: username generation, password, OU placement, activation timing.

let idautoPersonUserNameMV = when {
    else -> (givenName.take(1).lowercase() + sn.stripDiacriticals().lowercase()).incrementOnCollision(20, 1)
}
let userPassword = givenName.lowercase().take(1) + sn.uppercase() + idautoPersonStuID.takeLast(4)
let pwdReset = true
let @ou = when {
    idautoDisabled == "TRUE" -> "OU=Disabled,DC=domain,DC=com"
    employeeType.contains("staff") -> "OU=Staff,DC=domain,DC=com"
    else -> "OU=Students,DC=domain,DC=com"
}
let @activationOffset = when {
    employeeType.contains("staff") -> 259200
    else -> -1
}
```

### Publication Rule (ID Store → Sink System)
```
ruleID = <adapter-guid>
ruleType = person

// Publication: ID Store → <SinkSystemName>
// Maps IDHub standard attributes to <sink> schema.

let sAMAccountName = idautoPersonUserNameMV
let userPrincipalName = idautoPersonUserNameMV + "@domain.com"
let givenName = givenName
let sn = sn
let displayName = displayName
let mail = idautoPersonUserNameMV + "@domain.com"
let @ou = when {
    employeeType.contains("staff") -> "OU=Staff,DC=domain,DC=com"
    else -> "OU=Students,DC=domain,DC=com"
}
```

### Correlation Rule (Source System ↔ ID Store)
```
ruleID = <uuid>
ruleType = person

// Correlation: match incoming <source> records to existing ID Store identities.

let key exact a idautoPersonStuID = sourcedId
let key exact b idautoPersonHRID = identifier
```

---

## Validating Generated MR Against the Real Compiler

If a local checkout of `idhub-provisioning` (the PVP repo) is available, don't just eyeball
generated MR for correctness — compile it. The `mrt` CLI tool parses an `.mr` file through the
real ANTLR grammar and prints the generated Kotlin, catching grammar errors and letting you
verify a built-in resolves the way you expect (e.g. whether a `when` branch targeting a
multi-valued attribute needs a list literal or a plain scalar — it doesn't, confirmed
2026-09-17, see `references/patterns.md`'s "Preserve Existing Multi-Valued Attribute" pattern):

```bash
./gradlew :provisioning-tools:run --args="mrt -t <type> -c <ClassName> -f <file.mr>"
```

`<type>` is one of: `ingest`, `source-match`, `policy`, `publish`, `sink-match-disjunction`.
`<file.mr>` needs a real header (`ruleID = <uuid>` / `ruleType = person`) — a bare fragment of
`let` statements won't compile standalone. `BUILD SUCCESSFUL` with generated Kotlin printed to
stdout means the grammar and built-ins resolved as written; a grammar error surfaces immediately
instead of failing silently at runtime. Trim large lookup tables to a representative few branches
when compile-checking — the grammar validates the same way regardless of table size.

## Reference Files

- `references/builtins.md` — Quick-reference table of every built-in with signature and example
- `references/patterns.md` — Extended real-world patterns for common scenarios
- `references/debugging-pvp-logs.md` — How to triage a `pvp.log` (PVP run log) for the root
  cause of failures without reading the whole file — these logs can be hundreds of MB to
  >1GB. Read this before grepping a `pvp.log` for the first time in a session.

Read these if you need more detail on a specific built-in or pattern beyond what's in this file.
