# Security review and changes — 18 October 2026

## 3.1 additions

The new host inventory endpoint requires admin authentication, executes only fixed
Windows commands without a shell/user-provided command text, excludes saved Wi-Fi
keys and does not expose its raw command output. The LAN web-port check requires
admin + CSRF, a saved RFC1918 IP, fixed ports/timeouts and a rate limit. It never
follows URLs, redirects or supplies router credentials. Its response distinguishes
reachability from device identity. Policy previews use the existing authorization
engine and have no network side effects. Browser options are rendered as text;
manual labels never substitute for observed SSIDs.

Windows deep links require the person at the browser to complete any permission
prompt. No Windows permissions, services or physical router settings were changed.

Reviewed using the installed `claude-security` skill (Codex-compatible adaptation
of the Claude Security guidance). Scope: local launcher, FastAPI authentication,
admin CRUD, portal, session binding, gateway authorization, CSV exports and changed
frontend rendering. No source or credentials were sent to external review services.

Confirmed paths and remediations:

Source entry points: `app/main.py` — `setup` (line 260), `login` (294),
`change_password` (319), `update_user` (386), `delete_user` (405),
`toggle_voucher` (440). Guest/integration paths: `guest_login`, `gateway_bind`,
`gateway_authorize`, `export_csv` in the same file; rate limiting is
`app/security.py:rate_allowed`. Line numbers refer to this update and can shift.

| Severity | Original behavior / precondition | Change | Confidence |
| --- | --- | --- | --- |
| High | A LAN visitor could claim the first admin when the unconfigured server was exposed | Initial setup requires a loopback client; finish setup locally before exposing the service | High |
| High | A disabled/deleted account or disabled voucher retained authorized sessions | Revoke associated sessions; authorization also checks current credential state | High |
| High | User-scoped restrictions used an asserted owner/user rather than the verified guest | Derive user scope from the active gateway-verified session during network authorization | High |
| High | Binding accepted a predictable session ID with no server-enforced login possession proof; an adapter trusting client IDs could bind another session | Require a random one-time bind proof, store its digest and atomically consume it | High; station identity still depends on adapter |
| Medium | Admin password change left other stolen admin sessions valid | Invalidate all other sessions on successful password change | High |
| Medium | Per-IP-and-username rate limits could be spread across usernames; rate state grew indefinitely | Additional per-IP/per-account limits, bounded memory and a lock; throttle password changes | High |
| Medium | User-controlled CSV cells could execute formulas when opened in spreadsheets | Prefix formula-like text cells with an apostrophe | High |
| Low | Null password updates raised errors; a guest-supplied MAC could overwrite existing inventory metadata | Reject null guest updates before hashing; preserve existing device details on guest login | High |

Also reject cross-origin writes, reduce missing-user timing differences with a dummy
password hash, and include expired sessions in gateway disconnect state. Regression
tests exercise these authorization boundaries and heartbeat freshness.

Remaining boundaries: no MFA, single admin, in-process rate limiting (use one worker
or external distributed limiting), HTTPS/network isolation configured separately,
no deployed hardware connector, no hardware penetration test, and no independent
dependency audit. The gateway key is a powerful trusted-service credential. A
compromised gateway can report false telemetry or bypass its own firewall.
Heartbeat capability claims are never proof of enforcement. Do not deploy public
HTTP or infer security certification from passing tests.

Existing unbound sessions created before the binding-proof upgrade must log in
again to obtain a proof. Adapters must update their `/bind` request contract.
