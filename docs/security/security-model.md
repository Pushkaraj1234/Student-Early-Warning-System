# Security & Privacy Model

> Status: **PROPOSED v0.1**. This is an engineering document, **not legal advice**. Before any real student data is processed, the institution's legal or data-protection lead must review §6.

## 1. Assets

| Asset | Sensitivity |
|---|---|
| Student identity and academic records | High |
| Risk predictions and explanations | High (stigmatising if leaked) |
| Intervention notes | High (free text may contain sensitive information) |
| Protected attributes (only if approved for fairness auditing) | Very high |
| Supabase secret (service-role) key, database password, access tokens | Critical |
| Model artifacts | Medium (may encode training-data properties) |

## 2. Threat model (summary)

| Threat | Mitigation |
|---|---|
| Client tampering or reverse-engineering the app | The client holds only the publishable (anon) key. All authorisation is enforced by RLS and on the server |
| Horizontal access (a mentor reading non-assigned students) | RLS based on `mentor_assignments` and `institution_members`; pgTAP tests assert that it is **denied** |
| Cross-institution access | `institution_id` is checked in every policy; tests cover it |
| Privilege escalation through editable metadata | Roles are never read from `user_metadata`. Only admins can write `institution_members` |
| Leaked service-role key | Never in Flutter, Git or logs. Stored only in the server's secret store. Rotated on suspicion |
| Tampering with predictions | `risk_predictions` has no client insert, update or delete policy. Written only by the server job; audited |
| Forged JWT against FastAPI | Signature, issuer, audience and expiry are verified on every request. Role is checked against the database, not trusted from the client body |
| Injection | Parameterised queries only. Pydantic validation in FastAPI. Input validation in Flutter for UX only; the server/database is authoritative |
| Storage leakage | Private buckets only. Storage RLS policies. Short-lived signed URLs |
| Personal data in logs or analytics | Structured logging with a denylist of personal fields. No third-party analytics SDK without approval |
| Re-identification from research exports | De-identification, removal of small cells, and restricted access under the data-sharing agreement |

## 3. Key and secret handling

| Secret | Where it may live | Where it must never appear |
|---|---|---|
| Supabase URL | Anywhere (not secret) | — |
| Publishable key (`sb_publishable_…`) or legacy `anon` key | Flutter build config (`--dart-define-from-file`, git-ignored file) | — (safe for clients **only because** RLS is enforced) |
| Secret key (`sb_secret_…`) or legacy `service_role` key | Server secret store / server env only | Flutter, Git, CI logs, docs, chat |
| Database password, `SUPABASE_ACCESS_TOKEN` | Developer machine env / CI secret | Git |

- `.gitignore` excludes `.env`, `.env.*` (except `.env.example`) and `*.local.json`.
- Only templates (`*.example`) are committed, with placeholder values.

## 4. Database security rules

1. RLS is enabled on **every** table in an exposed schema, in the same migration that creates it.
2. `anon` is granted nothing on application tables.
3. `security definer` functions:
   - live in the non-exposed `private` schema;
   - set `search_path = ''`;
   - use fully qualified names;
   - have `execute` revoked from `public` and `anon`.
4. Views over RLS-protected tables use `security_invoker = true`, so that RLS is not bypassed.
5. Never disable RLS to "make a feature work". Fix the policy instead.
6. Every policy has pgTAP tests for allowed **and** denied cases, for each role.

## 5. Application security rules

- **Flutter:** no secrets; tokens are held only by `supabase_flutter`'s session storage; certificate validation is left at platform defaults; release builds are obfuscated (`--obfuscate --split-debug-info`) as defence in depth, not as a security control.
- **FastAPI:** CORS is closed by default (a mobile client does not need it); request size limits; rate limiting on scoring endpoints; errors never echo internal details or personal data.
- **Dependencies:** pinned; reviewed on upgrade; vulnerability scanning in CI (**[OPEN]**: tool).

## 6. Privacy & legal (India)

- **Applicable law:** India's Digital Personal Data Protection Act, 2023 (DPDP Act) and the rules notified under it. The applicable obligations and their commencement dates **must be confirmed by legal counsel**. This document does not determine compliance.
- **Children:** if the target population includes anyone under 18, the DPDP Act requires verifiable parental or guardian consent. It also restricts tracking and behavioural monitoring of children, subject to exemptions defined in the rules. An early-warning system can be seen as behavioural monitoring. **Whether an exemption applies must be established before any processing of minors' data.** This is why the target population is the first open decision in `project-scope.md`.
- **Purpose limitation:** data is used only for student support and approved research, as stated in the consent notice.
- **Consent and notice:** records are kept in `consents`. Withdrawing consent stops future processing.
- **Data principal rights:** there must be processes for access, correction and erasure requests, handled through the institution.
- **Data residency:** the Supabase project region and the FastAPI hosting region are **unverified** (**[OPEN]**). Confirm them against the institution's policy.
- **Research ethics:** institutional ethics approval (IRB/IEC) is required before `institutional` data is used for research, and before any mentor or student usability study.

## 7. Prerequisites before real student data (phase 6 gate)

- [ ] Target population decided; legal review of DPDP obligations (including rules on children, if applicable) completed
- [ ] Data-sharing agreement signed with the partner institution
- [ ] Ethics approval obtained
- [ ] Consent/notice text approved, and the consent capture flow implemented
- [ ] Supabase region and FastAPI hosting confirmed to meet residency requirements
- [ ] RLS test suite passes for all roles and tables
- [ ] Incident-response contact and breach-notification procedure documented
- [ ] Separate staging project in use for all testing, so production holds real data only

## 8. Incident response (outline)

1. Contain: rotate keys and revoke sessions.
2. Assess scope using `audit_log` and the Supabase logs.
3. Notify the institution's data-protection contact. Legal counsel determines statutory notification duties.
4. Write a post-incident review and add a regression test.
