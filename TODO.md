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

<!-- No open items. -->

## Processed

- [x] Document the `Can't redefine property 'if.else'` failure mode more prominently — added a
  callout under § if / while / break covering the specific cause (hand-authored `if/else if/else`
  attaches the default block to the outer `if` instead of the inner nested `if`, since Connect has
  no native `else if`), plus a wrong/right XML example, a Quick Reference row, an updated checklist
  item 18, and a new Common Pitfalls row. Context: hit this in a customer's FnLoadTargetData.xml.
  (queued 2026-07-06, processed 2026-07-06)
