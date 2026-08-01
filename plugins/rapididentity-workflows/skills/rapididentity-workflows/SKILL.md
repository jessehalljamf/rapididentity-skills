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
| Entitlement creation (3-step API) | § Entitlement Creation |
| Common mistakes | § Common Pitfalls |

---

## Workflow JSON Structure

A workflow is a flat array of action objects. Each action has an `id`, `type`, `name`, and
routing fields that form the directed graph.

```json
{
  "name": "My Workflow",
  "description": "One-sentence description.",
  "actions": [
    { "type": "startAction", "id": "start", "name": "Start Action", "nextActionId": "<first-action-id>" },
    { "type": "endAction",   "id": "end",   "name": "End Action" },
    { "type": "failAction",  "id": "<uuid>","name": "Failed", "nextActionId": "end" },
    ...
  ]
}
```

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
See § advancedDssAction for full details.

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

The complete set of accepted prefixes is `resource`, `recipient`, `requestor`, `requester`,
`addressee`, `approver`, `approval` (`WorkflowExpressions.java:51-58`), plus a fallthrough that
resolves anything else — notably `dss.*` and `form.*` — from the request context. Matching is
case-insensitive; `requestor` and `requester` are exact synonyms.

| Scope | Contents |
|---|---|
| `%{form.*}` | Form field values submitted by the requester |
| `%{request.*}` | Workflow request metadata (e.g. `%{request.comments}`) |
| `%{requester.*}` | Requester's RI account attributes (e.g. `%{requester.mail}`). On a **proxied** request this resolves to the proxy actor, not the stored requester |
| `%{recipient.*}` | Recipient's RI account attributes (e.g. `%{recipient.dn}`) — the person the entitlement is *for* |
| `%{resource.*}` | The entitlement being requested (e.g. `%{resource.name}`) |
| `%{addressee.*}` | The **current approval task's** addressee — not a request participant |
| `%{approver0.*}` | The user who acted on the first approval step |
| `%{approval0.*}` | Attributes from the first approval step (e.g. `%{approval0.comments}`) |
| `%{dss.*}` | Return fields from the most recent `advancedDssAction` call |

Nested paths walk LDAP: `%{recipient.manager.mail}` fetches `manager` off the recipient's DN, then
`mail` off that DN. `dn`, `id`, and `idautoid` are terminal (no LDAP lookup).

> **Requester vs recipient.** These are separate identities on every request — a self-request is
> just the case where they're equal. When a user requests *on behalf of* someone else, `recipient`
> is the other person. Two consequences that bite: entitlement ACLs are evaluated against the
> **recipient**, and `%{requester.manager}` is not `%{recipient.manager}`. See the KB article
> `rapididentity/requests/recipients-and-on-behalf-of.md`.

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

- `expirationDays: -1` means no expiration
- `escalationDays: -1` means no escalation
- `onApproveId` and `onDenyId` route to different action nodes based on the decision
- After the approval step resolves, `%{approval0.comments}` contains the approver's comments

### Approver types — only three exist

`Approver.groovy:40-44` registers exactly three Jackson subtypes:

| `approver.type` | Shape |
|---|---|
| `userApprover` | `"user": { "id", "dn", "name" }` |
| `groupApprover` | `"group": { "id", "dn", "name" }` |
| `expressionApprover` | `"expression": "%{...}"` |

> **There is no `managerApprover` or `recipientApprover`.** Both are commonly assumed (and were
> wrongly documented in the KB until 2026-08-01) but neither exists in the codebase — posting either
> fails Jackson subtype resolution. Route dynamically with `expressionApprover` instead.

```json
"approver": { "type": "expressionApprover", "expression": "%{recipient.manager}" }
```

| Intent | Expression |
|---|---|
| Recipient's manager (usual intent for on-behalf-of flows) | `%{recipient.manager}` |
| Requester's manager | `%{requester.manager}` |
| The recipient themself | `%{recipient}` |

Pick deliberately — on an on-behalf-of request `%{requester.manager}` routes to the *requesting*
manager's own manager, which is rarely what's wanted.

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

Standard operations: `MATCHES_ANY_REGEX`, `EQUALS`, `NOT_EQUALS`, `CONTAINS`.

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
  "nextActionId": "<uuid>"
}
```

- `toList` is an array of addresses; supports `%{}` variable references
- `message` is a full HTML string — inline all CSS, no external stylesheets
- Workflow variables are substituted into the HTML at send time

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

**Binding values:**

| Value | Meaning |
|---|---|
| `MULTI_UNBOUND` | User can request multiple times; each request is independent |
| `SINGLE_BOUND` | User can only hold one grant at a time |

> **ACLs are evaluated against the recipient.** The `acl` block above (and any category ACL) is
> checked against the person the entitlement is *for*, not the person submitting the request
> (`StartWorkflowRequestValidator.groovy:317-327` → `ResourceVisibilityEvaluator`). Scope group and
> filter ACLs to the population that should **receive** the entitlement. A manager requesting for a
> report gets `400 Entitlement '...' is not visible to '<report name>'` when the report falls
> outside the ACL, even though the manager is inside it.

---

## Submitting a Request (including on behalf of another user)

```
POST /api/rest/workflow/tasks/startTask
{ "requestItems": [ {
    "type": "GRANT",
    "recipientId": "<recipient idautoID>",
    "resourceId": "<entitlementId>",
    "comments": "Requested on behalf of new hire",
    "requestForm": { "requestFormItems": [ { "name": "startDate", "value": "2026-08-15" } ] }
} ] }
```

- Note the base path is `/api/rest/workflow/...` — **not** the `/api/rest/admin/workflow/...` used
  by the definition/entitlement admin endpoints above.
- `recipientId` is the **idautoID** (not a DN, not a UUID). Set it to another user for on-behalf-of;
  the requester comes from the auth context and is never in the body.
- `requestItems` is a list — one call can batch multiple recipients/resources.
- `type` is `GRANT` or `REVOKE`; `REVOKE` also requires `previousRequestId`.

**Who may request for whom** (`StartWorkflowRequestValidator.groovy:249-279`): a non-privileged
requester may only target **themself or a direct report** (LDAP `manager` attribute).
`ADMIN`, `TENANT_ADMIN`, `WFM_ADMIN`, and `WFM_HELPDESK` may request for anyone. There is nothing in
between — arbitrary delegation requires one of those roles or a service-identity front-end.

**Finding valid recipients:** use `GET /api/rest/workflow/directReports/searchTask?criteria=` and
`GET /api/rest/workflow/directReports/users/{id}/associations` (which returns each resource with a
`notRequestable` flag). Do **not** use `/users/searchTask` — it is an org-wide people search that is
not filtered to users the caller may request for, so selections from it get rejected at submit time.

There is no "what can I request for user X" endpoint; the requestables search endpoints take no
recipient parameter. Full detail: KB `rapididentity/requests/recipients-and-on-behalf-of.md`.

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
| `400 Entitlement '...' is not visible to '...'` | The **recipient** doesn't match the entitlement's group/filter ACL. ACLs evaluate against the recipient, not the requester — re-scope the ACL to who should *receive* it. |
| `403 You are not allowed to request entitlements for '...'` | The requester is neither the recipient nor their manager, and lacks `WFM_ADMIN`/`WFM_HELPDESK`/`ADMIN`/`TENANT_ADMIN`. |
| `approver.type: "managerApprover"` rejected | That type doesn't exist. Use `{ "type": "expressionApprover", "expression": "%{recipient.manager}" }`. |
| Manager approval routed to the wrong person | On an on-behalf-of request, `%{requester.manager}` is the requesting manager's *own* manager. Use `%{recipient.manager}`. |
| Connect action set can't see the recipient | Nothing is auto-injected — pass it explicitly, e.g. `recipientdn='%{recipient.dn}'`. |
