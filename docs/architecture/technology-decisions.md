# Technology Decisions

> Format: lightweight ADRs (architecture decision records).
> **Accepted (mandated)** = required by the project brief.
> **Proposed** = recommended by this document, awaiting owner confirmation.
> **[OPEN]** = not decided.

## Environment observed during phase 0 (2026-09-24)

| Tool | Found | Version |
|---|---|---|
| Flutter | yes | 3.41.4 (stable), Dart 3.11.1 |
| Python | yes | 3.13.2 |
| Git | yes | 2.53.0 |
| Node.js | yes | (present; can run the Supabase CLI via `npx supabase`) |
| Supabase CLI | **no** | — |
| Docker | **no** | — (required for a local Supabase stack and `supabase test db`) |
| OS | Windows 11 | iOS builds require macOS — **not possible on this machine** |

---

### ADR-001 Mobile client: Flutter — **Accepted (mandated)**
- Android is the first target, because it can be built and tested on this Windows machine. iOS needs a macOS build host (**[OPEN]**).
- Static analysis uses `flutter analyze` with a strict lint set, `strict-casts`, `strict-inference` and `strict-raw-types`.

### ADR-002 Backend platform: Supabase — **Accepted (mandated)**
- Supabase provides Auth, PostgreSQL, RLS, Storage and Realtime.
- The existing project URL is `https://rzekfmfuskknadrchkhg.supabase.co`.
- Client package: `supabase_flutter`. Pin the version in `pubspec.yaml` at scaffolding time.

### ADR-003 Schema management: Supabase CLI migrations — **Proposed**
- Location: `supabase/migrations/<timestamp>_<name>.sql`, applied with `supabase db push` after `supabase link`.
- Every migration is **idempotent** (see `docs/database/database-design.md` §6).
- The CLI is not installed. The options are `npx supabase …` (Node is present) or a standalone install. **[OPEN]**: the owner decides.

### ADR-004 RLS authorisation pattern — **Proposed**
- Roles and memberships are stored in tables, not in client-editable user metadata.
- Policies call `security definer` helper functions in a **non-exposed** `private` schema, with a pinned empty `search_path`.
- `auth.uid()` is wrapped as `(select auth.uid())` so the planner evaluates it once per statement.
- A custom access-token hook that puts roles into JWT claims is a possible later optimisation. It is not the source of truth.

### ADR-005 Flutter state management and routing — **Proposed**
- State: `flutter_riverpod`. It is testable, supports dependency injection and has no `BuildContext` coupling.
- Routing: `go_router`, with auth- and role-based redirects.
- Immutable models: `freezed` + `json_serializable`, or hand-written classes. **[OPEN]**: `freezed` adds a build step.
- Structure: feature-first (`lib/features/<feature>/{data,domain,presentation}`), with a thin repository layer over Supabase.
- These are recommendations. The owner may pick alternatives before phase 5.

### ADR-006 ML stack: Python, scikit-learn, XGBoost, SHAP — **Accepted (mandated)**
- The Python version is pinned per service, to one that **all three** libraries publish wheels for. Wheel availability for Python 3.13 must be checked at setup time, not assumed.
- Dependencies are pinned in a lock file. Tooling: `ruff` (lint and format), `mypy --strict` (types), `pytest` (tests).
- Explanations: `shap.TreeExplainer` for XGBoost. Coefficients or SHAP `LinearExplainer` for logistic-regression baselines.

### ADR-007 Inference service: FastAPI — **Accepted (mandated)**
- Pydantic models give explicit request and response contracts, and OpenAPI is generated from them.
- JWT verification for Supabase tokens: verify against the project's JWKS if asymmetric signing keys are enabled, otherwise against the project's JWT secret. The project's signing configuration has not been inspected. **[OPEN]**
- Hosting: **[OPEN]** (e.g. a container platform). This must satisfy the data-residency decision.

### ADR-008 Predictions are pre-computed and stored — **Proposed**
- See `system-architecture.md` §4. The app reads `risk_predictions` through RLS. The FastAPI on-demand path is optional and restricted to staff.

### ADR-009 Model registry — **Proposed**
- Start with file-based artifacts plus a `model_versions` table holding metadata: model, dataset, feature versions, training timestamp, metrics and model-card path.
- Move to MLflow later only if the number of experiments justifies it.

### ADR-010 Version control and CI — **Proposed**
- Git, with a `main` branch protected once a remote exists (none exists yet). CI (**[OPEN]**: e.g. GitHub Actions) runs analyse, test and build for each package.
- Secrets never go into Git. `.env*` and `*.local.json` are ignored. Only `*.example` templates are committed.
