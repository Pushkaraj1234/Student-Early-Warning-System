# Architecture Assessment — Phase 0 Repository Inspection

> Date: 2026-09-24. Inspector: Claude Code (lead architect role).
> Method: I listed the working directory and checked the installed toolchain. I also probed the Supabase project endpoint without credentials. No files were modified or deleted during inspection.

## 1. Existing project structure

- `D:\RM` was **empty**: no files, no hidden files, and **not a git repository**.
- Created in phase 0 (documentation only): `README.md`, `.gitignore` and `docs/**`.

## 2. Existing technologies

| Item | Finding |
|---|---|
| Application code | None |
| Flutter / Dart | 3.41.4 stable / 3.11.1 installed |
| Python | 3.13.2 installed |
| Git | 2.53.0 installed; repository **not initialised** |
| Node.js | Installed |
| Supabase CLI | **Not installed** |
| Docker | **Not installed** |
| Supabase project | `https://rzekfmfuskknadrchkhg.supabase.co` is reachable. `/rest/v1/` and `/auth/v1/health` return **HTTP 401 "No API key found"**, which confirms that the project exists and requires a key. **No key was provided, so the schema, RLS state, auth settings, region and key type (legacy JWT vs publishable/secret) could not be inspected.** |

## 3. Existing working functionality

**None.** There is no code, schema (as far as can be verified), model or build to preserve.

## 4. Missing functionality

Everything is missing: the Flutter app, the Supabase migrations and RLS policies, RLS tests, the FastAPI service, the batch scoring job, the ML pipeline, datasets, the synthetic data generator, CI, and environment templates.

## 5. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **Unknown remote schema.** The Supabase project may already contain tables or policies (e.g. made in the dashboard). Migrations written blindly could collide with them or duplicate them | High | Link the CLI and run `migration list` / `db pull` before the first migration |
| R2 | **Undecided target population.** Minors trigger DPDP consent and behavioural-monitoring restrictions | High | Owner decision + legal review before institutional data |
| R3 | **Undefined label and decision points** | High | Owner decision before any training |
| R4 | **No Indian institutional data.** Research claims are limited to benchmark method development; RQ5 cannot be answered | High (research) | Secure a partner institution and ethics approval early. Label all results by provenance |
| R5 | **Temporal leakage** in benchmark experiments (e.g. OULAD `date_unregistration`, the unknown grade-release lag) | High | As-of feature function, out-of-time splits, automated leakage tests (ML strategy §3) |
| R6 | **No Docker.** No local Supabase stack, and pgTAP RLS tests cannot run locally | Medium | Install Docker Desktop, or run RLS tests against a dedicated remote staging project |
| R7 | **Single Supabase project.** No dev/staging separation, so test data could mix with future real data | Medium | Create a separate staging project; keep synthetic data out of production |
| R8 | **Windows-only host.** No iOS builds | Medium | Android first; a macOS CI runner or host later |
| R9 | **Python 3.13 wheel availability** for XGBoost or SHAP is unverified | Low–Medium | Check at setup; pin a supported version |
| R10 | **Region / data residency** unverified | Medium | Check the project region in the dashboard |
| R11 | **Ethical harms** (labelling, feedback loops, proxy discrimination) | High | Supportive framing, human-in-the-loop, subgroup audits, intervention tracking |

## 6. Recommended architecture

As documented in [system-architecture.md](system-architecture.md):

- a monorepo with `apps/mobile`, `services/ml-api`, `ml`, `supabase` and `docs`;
- Supabase as the authoritative data and authorisation layer (RLS with `private`-schema helper functions);
- predictions pre-computed by a server-side batch job using a **shared as-of feature library**, stored immutably with full version lineage;
- the Flutter app reading only through RLS with the publishable key;
- a FastAPI service verifying Supabase JWTs, with the secret key confined to the server.

## 7. Exact next phase — Phase 1: Foundations

**Blocked on these owner inputs.** I will not invent them:

1. Target population (school vs higher education). Decides the consent model.
2. Primary label and decision points. Needed by phase 3; can be deferred briefly.
3. Whether `rzekfmfuskknadrchkhg` is dev/staging or production, and permission to create a second project.
4. Supabase access for the CLI (the developer runs `npx supabase login` and `link` interactively). Nobody pastes the secret key into chat.
5. Whether to install Docker Desktop.

**Phase 1 tasks (once unblocked):**

1. `git init`; first commit of the docs.
2. Link the Supabase CLI. **Inspect and record the existing remote schema** (`migration list`, `db pull`), then reconcile it with `database-design.md`.
3. Scaffold `apps/mobile`: `flutter create`, strict `analysis_options.yaml`, `supabase_flutter`, config through `--dart-define-from-file`, and an empty app shell with loading/error states. Verify with `flutter analyze`, `flutter test` and `flutter build apk --debug`.
4. Scaffold `services/ml-api` and `ml`: a pinned Python environment; `ruff`, `mypy --strict` and `pytest` configured; a health endpoint with a test.
5. First migration: `private` schema, `institutions`, `profiles`, `institution_members` + RLS + helper functions + pgTAP tests.
6. CI workflow running all of the analysis and test commands above.
