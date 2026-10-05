---
type: sop
id: SOP-2032
title: Audit an application's security
created: 2026-09-26
owner: vex
uses: ["[[SOP-1013-connect-an-external-tool-via-mcp]]", "[[SOP-1006-start-work-and-archive-a-wip-folder]]"]
skill_name: vex-security-audit
skill_summary: "Audit an application's credentials, authorization, integrations and data handling, with proof and a fix for every finding."
skill_triggers:
  - "audit my app for security"
  - "is my app safe to launch"
  - "RLS audit"
  - "I think a key leaked"
  - "security audit"
---

# SOP-2032 Audit an application's security

Vex's audit of an application the user builds or runs: credentials,
authorization, integrations and data handling, with proof for every
finding and a fix for each. Shipped by the Vex expansion pack; the
pack number range is explained in the pack's README.

Runs when the user says "audit my app / database / API for security",
"is this safe to launch", "I added a webhook, is it secure", "RLS
audit", "I think a key leaked".

The phases run in order. An earlier finding changes the later ones: a
leaked admin key makes the whole authorization review moot until it is
rotated.

1. [JUDGEMENT] **Scope.** Name what is audited (repository, database,
   deployed endpoints, integrations) and what is not, and the exact
   version (commit id, deployed build), and confirm with the user.
   Proof in later steps runs against a local or test environment the
   user names, never against production data without their explicit go.
2. [JUDGEMENT] **Credential hygiene.** Before anything else.
   - Search the code and config for secret-shaped strings: provider
     prefixes (for example `sk-`, `ghp_`, `xoxb-`, `AKIA`, `AIza`,
     `sk_live_`), and words like `secret`, `password`, `api_key`,
     `service_role`, `Bearer`.
   - Before trusting a scanner's zero, feed it a fake secret in two or
     three shapes (alone on a line, followed by more text, inside a
     quoted string) and see which it catches. A scanner that only reads
     new changes never sees history: run one full-history scan when a
     project is imported or first audited.
   - Check version history for a committed `.env`: a secret that was
     ever committed is public, even if the file is ignored now. A hash
     of a secret or an address committed to history is still that
     secret or address to anyone who can guess the input.
   - Search this vault's notes too: a vault is not a secret store, and
     a key in a note is CRITICAL.
   - Confirm no admin or write-scoped key reaches a browser bundle;
     browser keys are public-role keys only. Build tools can read the
     whole environment: the list of variables allowed into the bundle
     belongs in the build config.
   - Ask where secrets really live. `.env` outside the repository, the
     OS keychain, or the host's secret manager are fine; a chat thread
     or an email is a finding.
   Report a found credential by location and kind, never by value, and
   give the rotation order.
3. [JUDGEMENT] **Authorization.**
   - List the protected resources: tables, routes, storage buckets,
     functions, RPC endpoints. What should require auth; what does?
   - For each table: row-level security on (or the platform's
     equivalent); one clear policy per action; the user-id function
     wrapped so it evaluates once (on Postgres,
     `(select auth.uid())`); columns used in policies indexed. A
     "draft" or "hidden" flag on a row is not a policy: a hidden row
     under a public read policy is public the moment it lands.
   - For each route: authentication before the handler, authorization
     on the specific resource after it, rate limiting, CORS limited to
     known origins on anything authenticated.
   - For each privileged path (a SECURITY DEFINER function, an admin
     route, a webhook handler that skips auth): read it line by line
     for injection, over-return and missing access checks. A privileged
     function that takes "whose data" as a parameter from its caller
     answers questions about anyone. If it can run with the caller's
     rights instead, it must.
   - Where data is copied or fanned out (a notification, a feed, a
     search index, a digest), the copy carries its own access rule and
     is checked on its own; a rule on the source table does not reach
     it.
   - Refusal conditions that combine several terms are tested with a
     NULL in each term: in SQL, `NOT (a AND b)` lets a row through when
     any term is NULL.
   - Prove each gap: the query run as an anonymous user or as the
     member it concerns, returning rows it must not, and the request and
     its response.
4. [JUDGEMENT] **Integrations and surface.**
   - Webhooks received: signature verified on every request, replay
     protection by event id, acknowledge fast and process after,
     errors that do not leak internals.
   - APIs called: least-privilege scopes, backoff on retry, logs that
     never contain the credential or the sensitive payload, redirects
     not followed off the pinned host.
   - Web surfaces: CSP, HSTS, `frame-ancestors`, Referrer-Policy,
     Permissions-Policy.
   - Every user-controlled input validated on the server, not only in
     the browser.
   - Release and CI paths: actions and dependencies pinned to a commit,
     not a movable tag; a signed build attests the commit it built;
     a hash recorded on a database row is the uploader's claim until
     the stored bytes are hashed again.
5. [JUDGEMENT] **Data handling.** Store only what is needed;
   encryption at rest for the database and any bucket holding personal
   data; TLS everywhere; a real deletion path (and what survives it in
   logs, analytics and backups); export of a user's own data; consent
   recorded and revocable where tracking exists; privileged actions
   logged; sample data in a demo treated as a real payload once it is
   sent anywhere. Vex reviews the technical controls; which ones the
   law requires is a question for a lawyer, and Vex says so.
6. [JUDGEMENT] **Report.** Write
   `YYYY-MM-DD-<app-slug>-security-audit.md` in the WiP folder that
   asked ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]]).
   The header names the audited version. Verdict line first, CRITICAL
   findings at the top, then each finding:

   ```
   ### [SEVERITY] <short title>
   Where: <file, table, endpoint>
   What: <one paragraph>
   Proof: <the query, request, file and line; never a secret's value>
   Fix: <specific, copy-pastable where it can be>
   Verify: <the same test, expected to fail after the fix>
   ```

   Close with what was not audited, so silence is not read as a pass.
7. [JUDGEMENT] **Hand off and re-verify.** No fix is applied without
   the user's approval; the implementing agent or the user applies it.
   Vex re-runs each proof against the fixed version and writes a new,
   dated section naming that version. A test that cleans up after
   itself must also undo what the rows' triggers wrote. A second-hand
   "fixed" is not closure.

A durable pattern goes into Vex's `Journal/`, never with a credential
in it; the session itself is logged by Larry at close.
