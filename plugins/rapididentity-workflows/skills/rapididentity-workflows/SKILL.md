---
name: rapididentity-workflows
description: >
  Author, edit, import, configure, and troubleshoot RapidIdentity portal workflows and their
  JSON definitions. Use this skill whenever the user asks to create or modify a workflow JSON
  file, configure workflow actions (DSS, approval, condition, email, notification), wire up
  valuePairs to pass data between workflow steps and Connect action sets, reference workflow
  variables like %{dss.*}, %{form.*}, %{requester.*}, %{recipient.*}, %{approval0.*}, or
  %{request.*}, or asks about entitlement creation, workflow flow logic, or email action HTML.
  Also trigger when the user asks how to configure an advancedDssAction, set up approval routing,
  wire conditions on dss.success, or debug a workflow that is not passing data correctly. If the
  user references a workflow JSON file or asks about %{} variable substitution in any context,
  use this skill.
---

# RapidIdentity Workflows — Authoring Skill

RapidIdentity portal workflows are JSON-defined automation sequences that run in response to
portal entitlement requests. They chain typed action nodes — DSS calls, approvals, conditions,
email sends — and pass data between steps using `%{variable}` substitution.

---

## Quick Reference

| Need | Go to |
|---|---|
| Workflow JSON structure | § Workflow JSON Structure |
| Action types and their fields | § Action Types |
| Variable reference syntax `%{}` | § Variable Reference Syntax |
| Passing data to/from Connect (DSS) | § advancedDssAction |
| Approval routing | § approvalAction |
| Condition branching on dss.success | § conditionAction |
| Email action HTML | § emailAction |
| Forms — form list, per-step visibility, item types | § Workflow Forms |
| Entitlement creation (3-step API) | § Entitlement Creation |
| Binding types, Extend/Reset semantics | § Entitlement Creation → § Expiration, Extend, and Reset |
| Ground-truth field names (live capture) | `references/live-capture-request-sponsored-account.md` |
| Common mistakes | § Common Pitfalls |

---

## Workflow JSON Structure

A workflow definition has two main arrays: `actions` (the directed graph) and `forms` (the form
list — see § Workflow Forms). Each action has an `id`, `type`, `name`, and routing fields.

```json
{
  "name": "My Workflow",
  "description": "One-sentence description.",
  "status": "ACTIVE",
  "actions": [
    { "type": "startAction", "id": "start", "name": "Start Action", "nextActionId": "<first-action-id>" },
    { "type": "endAction",   "id": "end",   "name": "End Action" },
    { "type": "failAction",  "id": "<uuid>","name": "Failed", "nextActionId": "end" },
    ...
  ],
  "forms": [ ... ]
}
```

Server-managed fields on an existing definition: `id` (UUID), `dn`, `version` (incremented by the
server on each PUT — no optimistic locking; last writer wins). When updating via
`PUT /api/rest/admin/workflow/workflowDefinitions/{id}`, the body **replaces the entire
definition** — always GET first, modify in memory, then PUT, or you will silently drop fields
(including the whole `forms` array).

**Required actions** — every workflow must include exactly one `startAction`, one `endAction`,
and at least one `failAction`. The `startAction.nextActionId` points to the first real step.

**Routing fields by action type:**

| Field | Used by |
|---|---|
| `nextActionId` | Most linear actions |
| `onTrueActionId` / `onFalseActionId` | `conditionAction` |
| `onApproveId` / `onDenyId` | `approvalAction` |

---

## Action Types

### `startAction`

```json
{ "type": "startAction", "id": "start", "name": "Start Action", "nextActionId": "<uuid>" }
```

### `endAction`

```json
{ "type": "endAction", "id": "end", "name": "End Action" }
```

### `failAction`

```json
{ "type": "failAction", "id": "<uuid>", "name": "Failed", "nextActionId": "end" }
```

### `advancedDssAction`

Calls a Connect action set and exposes its return value as `%{dss.*}` variables.
See § advancedDssAction for full details (including the simpler `dssAction` variant with
`resultValidationRegex`).

### `approvalAction`

Routes to `onApproveId` or `onDenyId` based on approver decision.
See § approvalAction for full details.

### `conditionAction`

Evaluates `operand1 OPERATION operand2` and routes true/false.
See § conditionAction for full details.

### `emailAction`

Sends an HTML email. See § emailAction for full details.

---

## Variable Reference Syntax

Workflow variables use `%{scope.field}` syntax and are resolved at runtime.

### Scopes

| Scope | Contents |
|---|---|
| `%{form.*}` | Form field values submitted by the requester |
| `%{request.*}` | Workflow request metadata (e.g. `%{request.comments}`, `%{request.id}`, `%{request.type}` = `GRANT`/`REVOKE`) |
| `%{requester.*}` | Requester's RI account attributes (e.g. `%{requester.mail}`). `%{requestor.*}` is an accepted alternate spelling seen in production — prefer `requester` in new work |
| `%{recipient.*}` | Recipient's RI account attributes (e.g. `%{recipient.dn}`) |
| `%{addressee.*}` | Alternate subject in certain request types (e.g. `%{addressee.idautoID}`) |
| `%{approvalN.*}` | Metadata from approval step N, **0-indexed** (e.g. `%{approval0.comments}`, `%{approval0.approver.dn}`) |
| `%{approverN.*}` | Account attributes of the user who acted on approval step N (e.g. `%{approver0.mail}`) — distinct from `approvalN` |
| `%{resource.*}` | The entitlement being requested (e.g. `%{resource.name}`) |
| `%{dss.*}` | Return fields from the most recent `advancedDssAction` call (`%{dss.result}` = raw return value) |
| `%{grant.form.*}` | **Revoke workflows only** — form values from the original Grant request |

**Nested attribute navigation** — requester/recipient attributes support dot navigation to related
objects: `%{recipient.manager.fullName}`, `%{recipient.manager.mail}`.

### Common variables

| Variable | Description |
|---|---|
| `%{form.givenname}` | First name from the request form |
| `%{form.idautopersonenddate}` | Expiration date from the request form |
| `%{request.comments}` | Requester-entered comments on the request |
| `%{requester.mail}` | Email address of the person who submitted the request |
| `%{recipient.dn}` | Full DN of the selected recipient/sponsor |
| `%{approval0.comments}` | Comments entered by the approver when approving or denying |
| `%{dss.success}` | `true` or `false` returned from the Connect action set |
| `%{dss.message}` | Message string returned from the Connect action set |
| `%{dss.idautoPersonClaimCode}` | Claim code returned from WFM action set |
| `%{dss.idautoPersonUsernameMV}` | Username returned from WFM action set |
| `%{dss.mail}` | Email address returned from WFM action set |
| `%{dss.portalURL}` | Portal URL returned from WFM action set |

> **Scope availability** — `%{approval0.*}` is only populated after an `approvalAction` has
> been reached. Never reference it in emails that fire before the approval step.

---

## `advancedDssAction`

Calls a Connect action set synchronously and maps its `JSON.stringify(results)` return value
into `%{dss.*}` variables.

```json
{
  "type": "advancedDssAction",
  "id": "<uuid>",
  "name": "Create/Update Account",
  "actionName": "WFMValidateAccount",
  "nextActionId": "<uuid>",
  "valuePairs": [
    "givenname='%{form.givenname}'",
    "sn='%{form.sn}'",
    "mail='%{form.mail}'",
    "requestcomments='%{request.comments}'",
    "approvercomments='%{approval0.comments}'",
    "requesteremail='%{requester.mail}'",
    "manager='%{recipient.dn}'"
  ]
}
```

**`valuePairs` syntax** — each string is `paramName='value'` where the value is a literal or
a `%{}` variable reference. Single quotes around the value are required.

**`actionName` rules** — the Connect action set name is typed **exactly**: case-sensitive, no
search, no autocomplete, and a typo fails only at runtime. For action sets in the MAIN project use
the bare name; for any other project the format is `ProjectName.ActionSetName` (dot separator
required).

**Optional fields** — `dssUrl` (empty string = the local Connect instance; a remote RI URL is
supported but rare), `username`, and `trace` (boolean; enables Connect execution tracing — useful
while debugging, leave off in production).

**Simple variant: `dssAction`** — same fields as `advancedDssAction` plus `resultValidationRegex`.
Instead of exposing `%{dss.*}` for a follow-up `conditionAction`, the action set's raw return value
must match the regex for the step to succeed. Use `advancedDssAction` + `conditionAction` when you
need to branch on structured output; `dssAction` when a single pass/fail regex on the return value
is enough.

**Validate-only pattern** — to call the action set for validation without writing, add
`"validateOnly='true'"` to the `valuePairs`. The `advancedDssAction` is then wired to a
`conditionAction` that checks `%{dss.success}`:

```json
{ "type": "conditionAction", "operand1": "%{dss.success}", "operation": "MATCHES_ANY_REGEX", "operand2": "true",
  "onTrueActionId": "<approval-step>", "onFalseActionId": "<notify-invalid-email>" }
```

**Connect action set requirements** — the backing action set must:
- Return `JSON.stringify(results)` from every exit path
- Set `results.success = true` on success, `false` on any failure
- Set `results.message` on every path
- Initialize `logColors` in `defineDefaultVariables` using `Object.assign` so all color keys are always present regardless of whether `Global.connectLogColorSchema` is configured:

```xml
<action name="setVariable">
  <arg name="name" value="logColors"/>
  <arg name="value" value="Object.assign({changedData:&quot;chocolate&quot;,complete:&quot;teal&quot;,counts:&quot;black&quot;,data:&quot;blue&quot;,debug:&quot;purple&quot;,error:&quot;red&quot;,fail:&quot;darkred&quot;,info:&quot;royalBlue&quot;,logOnly:&quot;slateGray&quot;,processing:&quot;steelBlue&quot;,query:&quot;darkcyan&quot;,skipped:&quot;mediumpurple&quot;,sourceData:&quot;dimGray&quot;,success:&quot;green&quot;,targetData:&quot;darkslategray&quot;,test:&quot;darkorange&quot;,warn:&quot;goldenrod&quot;,whitespace:&quot;white&quot;},Global.connectLogColorSchema||{})"/>
</action>
```

Defaults are the base; `Global.connectLogColorSchema` overrides individual keys when present. Reference colors as `logColors.keyName` on every `log` action's `color` arg. See the connect-action-sets skill for the full key reference table.

---

## `approvalAction`

Pauses the workflow and creates an approval task for the specified group or user.

```json
{
  "type": "approvalAction",
  "id": "<uuid>",
  "name": "Approval",
  "description": "Approval description shown to the approver.",
  "approver": {
    "type": "groupApprover",
    "group": {
      "id": "<group-idautoID>",
      "dn": "idautoID=<group-idautoID>,ou=Groups,dc=meta",
      "name": "Portal Sponsor"
    }
  },
  "expirationDays": -1,
  "escalationDays": -1,
  "onApproveId": "<next-action-on-approve>",
  "onDenyId": "<email-action-on-deny>"
}
```

- `expirationDays: -1` means no expiration; a positive value expires the approval task after N days
- `escalationDays: -1` means no escalation; with a positive value, add an `escalationApprover`
  object (same shape as `approver`) that the task escalates to after N days
- `onApproveId` and `onDenyId` route to different action nodes based on the decision
- After the approval step resolves, `%{approval0.comments}` contains the approver's comments

**`approver.type` values:**

| Type | Resolves to |
|---|---|
| `groupApprover` | Any member of the referenced group (shown above) |
| `userApprover` | A specific named user |
| `managerApprover` | The requester's manager (LDAP `manager` attribute) |
| `recipientApprover` | The recipient (target identity) of the request |

---

## `conditionAction`

```json
{
  "type": "conditionAction",
  "id": "<uuid>",
  "name": "If Successful",
  "operand1": "%{dss.success}",
  "operation": "MATCHES_ANY_REGEX",
  "operand2": "true",
  "onTrueActionId": "<uuid>",
  "onFalseActionId": "<uuid>"
}
```

Full `operation` enum: `EQUALS`, `NOT_EQUALS`, `MATCHES_ANY_REGEX`, `CONTAINS`, `STARTS_WITH`,
`ENDS_WITH`, `IS_NULL`, `IS_NOT_NULL` (the last two ignore `operand2`).

**`dss.success` check** — always use `MATCHES_ANY_REGEX` with `operand2: "true"` when branching
on a DSS result. String equality checks on boolean-like values are unreliable.

---

## `emailAction`

```json
{
  "type": "emailAction",
  "id": "<uuid>",
  "name": "Send Welcome Email",
  "from": "noreply@rapididentity.com",
  "toList": ["%{form.idautopersonhomeemail}"],
  "subject": "Welcome to RapidIdentity",
  "message": "<html>...</html>",
  "isHtml": true,
  "isCritical": false,
  "nextActionId": "<uuid>"
}
```

- `toList` is an array of addresses; supports `%{}` variable references
- `message` is a full HTML string — inline all CSS, no external stylesheets
- `isHtml: true` marks the body as HTML; `isCritical` defaults false
- Workflow variables are substituted into the HTML at send time

> **Field names live-confirmed 2026-07-28** against
> `GET /api/rest/admin/workflow/workflowDefinitions/{id}` on the sandbox tenant ("Request
> Sponsored Account" v4): `from` / `toList` / `subject` / `message` / `isHtml` / `isCritical`.
> Some API docs show `to`/`body` instead — that shape is wrong; do not use it.

### Comments section HTML pattern

Insert this block immediately before `<div class="footer">` to display requester and approver
comments in a styled section matching the standard detail card layout:

```html
<div class="section">
  <div class="section-title">Comments</div>
  <div class="details-card">
    <div class="detail-row">
      <div class="detail-label">Requester Comments</div>
      <div class="detail-value">%{request.comments}</div>
    </div>
    <div class="detail-row">
      <div class="detail-label">Approver Comments</div>
      <div class="detail-value">%{approval0.comments}</div>
    </div>
  </div>
</div>
```

> **Important:** Only include the Approver Comments row in emails that fire **after** the
> approval step. Emails triggered before approval (e.g. "Request Invalid") should include
> only the Requester Comments row — `%{approval0.comments}` will be empty at that point.

---

## Workflow Forms

A workflow definition carries a **form list** — a `forms` array of zero or more named forms. A
single workflow can define multiple forms, and the *entitlement* (resource) chooses which one to
show per request type via its dropdowns: **Grant Workflow Form**, **Extend Workflow Form**,
**Reset Workflow Form**, **Revoke Workflow Form**. Each dropdown is populated only with the forms
defined inside the currently selected workflow — switching workflows resets the form choice. Left
blank, no form is shown and the workflow runs without requester input.

```json
"forms": [
  {
    "id": "<uuid>",
    "displayName": "Request Sponsored Account",
    "workflowFormItems": [
      {
        "name": "givenname",
        "displayName": "First Name",
        "type": "STRING",
        "hideFromRecipient": false,
        "listElements": [],
        "requiredActionIds": ["start", "<approval-action-id>"],
        "editableActionIds": [],
        "hiddenActionIds": []
      },
      {
        "name": "idautopersonemployeetypes",
        "displayName": "Account Type",
        "type": "LIST",
        "hideFromRecipient": false,
        "listElements": [
          { "displayValue": "Contractor", "value": "Contractor" },
          { "displayValue": "Vendor", "value": "Vendor" }
        ],
        "requiredActionIds": ["start", "<approval-action-id>"],
        "editableActionIds": [],
        "hiddenActionIds": []
      }
    ]
  }
]
```

**Per-step visibility** — each form item lists the action-step ids where it is Required, Editable,
or Hidden (`requiredActionIds` / `editableActionIds` / `hiddenActionIds`). Live-captured
definitions list both `"start"` and the approval action's id in `requiredActionIds` (required at
submission AND shown as required to the approver), and use `editableActionIds` for optional
fields. Validation runs against the workflow's **Start action** specifically: missing required
fields, or values submitted for non-editable fields, reject the request before the workflow runs.

**Form item `type` values** — live-confirmed: `STRING`, `LIST` (with `listElements` of
`{displayValue, value}` pairs — the submitted value is `value`), `DATE_TIME`, `ATTACHMENT`.
API docs additionally list `INTEGER`, `BOOLEAN`, `USER`, `GROUP` (unverified). Note it is
`DATE_TIME` (emits a full ISO 8601 timestamp — trim with `.substring(0,10)` before REST calls)
and `ATTACHMENT`, not `DATE`/`FILE_ATTACHMENT` as some docs claim.

**Referencing values** — form items are identified by `name` (live captures show no separate id
field) and referenced in expressions as `%{form.<name>}`. Names must be unique within the
workflow; duplicates cause unpredictable resolution.

> **Round-trip warning:** because PUT replaces the whole definition, tooling that decodes a
> definition through a model missing the `forms` field will silently strip every form on the next
> save. Confirm forms survived after any programmatic update.

---

## Workflow Flow Patterns

### Validate → Approve → Create

The standard WFM workflow pattern:

```
Start
  → advancedDssAction (validateOnly=true)
  → conditionAction (%{dss.success} == true)
      true  → approvalAction
                approve → advancedDssAction (create)
                            → conditionAction (%{dss.success} == true)
                                true  → emailAction (success) → emailAction (welcome) → End
                                false → emailAction (failure) → failAction → End
                deny  → emailAction (denied) → failAction → End
      false → emailAction (invalid) → failAction → End
```

This pattern uses the same Connect action set for both the validate and create steps,
controlled by the `validateOnly` valuePair.

---

## Entitlement Creation

Entitlements (portal resources) are the portal-facing objects that make a workflow requestable.
Creating one requires three sequential API calls. The Grant Workflow **must be Active** before
the entitlement can be created — a 400 error with "Grant Workflow must be active" means the
workflow status has not been set to Active yet.

### Step 1 — Create Data Classification

```
POST /api/rest/admin/workflow/dataClassifications
{ "name": "Sponsorship", "description": "Sponsorship Workflows", "level": 0, "color": "0x000000" }
```

Capture the returned `id` as `classificationId`.

### Step 2 — Create Category

```
POST /api/rest/admin/workflow/categories
{ "name": "Create Sponsored Accounts", "description": "Create Sponsored Accounts", "status": "ACTIVE" }
```

Capture the returned `id` as `categoryId`.

### Step 3 — Create the Resource (Entitlement)

```
POST /api/rest/admin/workflow/resources
{
  "name": "Request Sponsored Account",
  "status": "ACTIVE",
  "binding": "MULTI_UNBOUND",
  "classificationId": "<classificationId>",
  "categoryIds": ["<categoryId>"],
  "grantWorkflowId": "<workflowId>",
  "acl": { "groupAclsEnabled": true, "groupAcls": [{ "id": "<groupId>", "name": "<groupName>" }] }
}
```

**Binding values** (per `Resource.groovy` — **fixed after creation**; changing requires
delete + recreate, losing existing grants):

| Value | Meaning | Revocable? |
|---|---|---|
| `SINGLE` | One active grant per user; re-requesting replaces it | Yes |
| `MULTI_BOUND` | Multiple grants, each tracked individually | Yes, individually |
| `MULTI_UNBOUND` | Multiple grants, **not tracked individually** | **No — cannot have a Revoke Workflow** |
| `COMPOSITE` | Container; requesting it auto-requests all child entitlements | Depends on children |

> An earlier version of this skill listed `SINGLE_BOUND` — the codebase enum is `SINGLE`. If a
> tenant rejects `SINGLE`, check what an existing entitlement returns from
> `GET /api/rest/admin/workflow/resources`.

### Expiration, Extend, and Reset (Time-based entitlements)

An entitlement's **Expiration** is `None`, `Time-based` (expires N days after grant), or
`Campaign-based`. With Time-based expiration, two more capabilities unlock on the resource:
**Allow Entitlement to be Extended** and **Allow Entitlement to be Reset**, each with its own
optional workflow + form dropdowns (Extend Workflow / Extend Workflow Form, Reset Workflow /
Reset Workflow Form).

| | Extend | Reset |
|---|---|---|
| New expiration | `currentExpiration + requestedPeriod` (additive) | `now + requestedPeriod` (restarts the clock) |
| Cap | Clamped per request to the resource's configured period (a warning is returned) | Same |

**Who may request** (either capability): the grant's recipient (self), the recipient's direct
manager, or a user with `WFM_ADMIN`, `WFM_HELPDESK`, `ADMIN`, or `TENANT_ADMIN`. Requests are
rejected if the association is inactive/already expired or the resource isn't Time-based.

**Blank/inactive workflow is fine** — the extension/reset still succeeds; the engine runs a
minimal Start→End graph and sends a canned notification email. The workflow hook is for *custom*
behavior, not required for the expiration change itself.

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| `%{approval0.comments}` empty in email | Email fires before the approval step. Remove the approver row from pre-approval emails. |
| `%{dss.success}` condition never matches | Use `MATCHES_ANY_REGEX` not `EQUALS` for boolean-like DSS return values. |
| valuePairs not passing data | Each pair must be `paramName='value'` — single quotes around the value are required. |
| DSS action returns no data | The Connect action set must return `JSON.stringify(results)` — a raw object or `null` return will not populate `%{dss.*}`. |
| Entitlement 400: Grant Workflow must be active | Set the workflow Status to **Active** before creating the entitlement resource. |
| Welcome email going to wrong address | Check `toList` — the welcome email should target `%{form.idautopersonhomeemail}`, not `%{requester.mail}`. |
| validateOnly step also sets approvercomments | Safe to include `approvercomments='%{approval0.comments}'` on the validate step — it will be empty and the action set's optional handling will skip it. |
| DSS action silently does nothing / runtime error | `actionName` is case-sensitive with no autocomplete; non-MAIN projects need `ProjectName.ActionSetName` with the dot separator. |
| PUT wiped the workflow's forms (or other fields) | PUT replaces the **entire** definition — GET, modify in memory, PUT. Confirm `forms` survived after any programmatic save. |
| Revoke Workflow dropdown missing/rejected | MULTI_UNBOUND entitlements cannot have a Revoke Workflow — grants aren't individually tracked. Use MULTI_BOUND if revocation matters. |
| Wrong binding chosen at creation | Binding is immutable — delete and recreate the entitlement (existing grants are lost). |
| Deactivating a workflow to stop a request | INACTIVE only blocks *new* requests; in-flight requests run to completion. |
| Extension request grants less time than asked | Requested period is clamped per request to the resource's configured Time-based period; also check Extend (additive) vs Reset (now + period) semantics. |
