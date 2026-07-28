# TODO — Skill Update Queue

Queue of proposed updates to the `connect-action-sets` skill. Add an entry whenever a new
pattern, pitfall, or correction is discovered during real Connect work but not worth stopping
to fix immediately. Process the backlog periodically: fold entries into `connect-action-sets/SKILL.md`
or the relevant `references/*.md` file, re-zip to `connect-action-sets.skill`, move the archived
copy into `archive/`, and check off or remove the entry here.

## How to add an entry

```
- [ ] Short description of the change. Context: where/why this came up. (YYYY-MM-DD)
```

## Queue

(empty)

## Processed

- [x] 2026-07-28 knowledge-base reconciliation pass: corrected `copyArray` from "deep copy" to
  **shallow copy** (SKILL.md tables + cheatsheet § copyArray; nested Records still shared);
  expanded `stringEscape` from 3 to the full **12 escape types** incl. `ldap-filter`/`ldap-dn`/`csv`
  (SKILL.md + cheatsheet); added § Built-in failure model (built-ins never throw — return
  undefined/false + set lastErrorMessage/lastErrorCode; `log level="ERROR"` clears-then-overwrites
  lastErrorMessage; getLastError* not cleared on read); added `return`-exits-entire-action-set to
  § Control Flow; strengthened § JavaScript & Engine Idioms with live-verified evidence (arrows +
  `new Set` in deployed `FnSyncGroupToTarget`/`SyncGroups`) and an explicit unverified-ES6+
  list; added 7 Common Pitfalls rows (failure model ×2, LATIN1 file encoding, getIdautoIDForUser
  not read-only, shallow copyArray, LDAP filter escaping). Source: Y:\ knowledge-base
  builtin-actions references (codebase-sourced, 2026-07-28) cross-checked against live tenant
  export evidence. (2026-07-28)

- [x] Correct the § Root Element guidance: a from-scratch action set must use the `<actionDefs>`
  (plural) wrapper root, not a bare `<actionDef>`. The skill currently says "Inside a `.dssproject`
  archive (actions/ folder) — bare `<actionDef>`," but a bare-root file **will not import through
  the Connect UI standalone importer**, and every on-disk manifest action set actually uses the
  wrapped form. Make `<actionDefs xmlns="urn:idauto.net:dss:actiondef"><actionDef name=… returnsValue=…
  description=…>…</actionDef></actionDefs>` the default for hand/generated XML (xmlns on the outer
  element only); note connect-api `build`/`convert`/`write_action_set`/`json_to_xml` with `wrap=true`
  emits it correctly; and state that `builtIn`/`community`/`category` and the `changeCount`/`modifiedMs`/
  `modifiedBy` reconciliation attributes are RI-saved metadata — do NOT add them to a from-scratch
  file. Context: authored FnPortalSession/FnWorkflowDefinitionHelper/FnEntitlementHelper for the
  rapididentity-connect Utilities project from scratch; all passed xmllint + validate_xml.py +
  connect-api build, but the Connect UI rejected the import until wrapped in `<actionDefs>`.
  (queued 2026-07-20, processed 2026-07-28 — § Root Element rewritten: wrapped form is the default
  for all from-scratch/hand-generated XML, bare root only encountered inside .dssproject archives,
  RI-saved metadata attributes called out as non-authoring inputs)

- [x] Document the `Can't redefine property 'if.else'` failure mode more prominently — added a
  callout under § if / while / break covering the specific cause (hand-authored `if/else if/else`
  attaches the default block to the outer `if` instead of the inner nested `if`, since Connect has
  no native `else if`), plus a wrong/right XML example, a Quick Reference row, an updated checklist
  item 18, and a new Common Pitfalls row. Context: hit this in a customer's FnLoadTargetData.xml.
  (queued 2026-07-06, processed 2026-07-06)
