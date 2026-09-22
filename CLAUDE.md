# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClusterVision is a web UI for managing Kubernetes users, RBAC permissions, and kubeconfig generation. It consists of a FastAPI backend (Python 3.12) and React frontend (Vite + TypeScript), deployed via Helm charts. All application state (login accounts, managed user registry, cluster registry, Vault config, access requests, audit logs) is stored in PostgreSQL. Native Kubernetes objects (RBAC, CSRs, ServiceAccount token Secrets) remain in Kubernetes.

## Development Commands

### Backend (FastAPI)
```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run dev server (requires PostgreSQL - see README.md)
export DATABASE_URL=postgresql+psycopg://postgres:dev@localhost:5432/postgres
uvicorn app.main:app --reload

# Run tests
pytest

# Run a single test file / test
pytest tests/test_access_request_service.py
pytest tests/test_access_request_service.py::test_create_request_starts_pending

# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Linting/formatting (ruff; not in requirements, install separately e.g. pipx install ruff)
ruff check .
ruff format .

# Database migrations (Alembic)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend (React + Vite)
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production (runs tsc first, then vite build)
npm run build

# Preview production build
npm run preview

# Type checking only
tsc --noEmit
```

There is no lint script/config on the frontend (no ESLint) — `npm run build`'s `tsc` step is the only static check.

### Docker
```bash
# Backend
docker build -t clustervision-backend backend/

# Frontend
docker build -t clustervision-frontend frontend/
```

## Architecture

### Backend Structure

**Core modules** (`backend/app/core/`):
- `auth.py` — JWT creation/validation, password hashing, role-based access control
- `dependencies.py` — FastAPI dependency injection (current user, admin gate)
- `audit_middleware.py` — Middleware that logs every mutating API request (actor, action, outcome), with request-body redaction for password/token/secret-like keys
- `async_utils.py` — Helpers for running blocking Kubernetes client calls off the event loop
- `exceptions.py` — Custom exceptions with HTTP exception handlers
- `kubernetes_client.py` — Kubernetes client factory (in-cluster or kubeconfig-based)
- `registry.py` — `RegistryMixin` class providing PostgreSQL-backed managed-user registry operations
- `csv_export.py` — CSV export utilities for audit and access-request compliance reports

**Services** (`backend/app/services/`):
- `auth_service.py` — Local user authentication (password + LDAP), default admin provisioning
- `ldap_service.py` — LDAP/AD bind and group membership resolution
- `certificate_service.py` — X.509 certificate user creation (CSR submission, approval, signing)
- `service_account_service.py` — Kubernetes ServiceAccount creation with long-lived token Secrets
- `rbac_service.py` — RBAC operations (list/create/delete ClusterRoles, Roles, bindings), user-centric assignment/revocation, SubjectAccessReview simulator
- `kubeconfig_service.py` — Kubeconfig file generation for certificate and ServiceAccount users
- `token_service.py` — Token audit trail (kubeconfig downloads) and ServiceAccount token lifecycle
- `vault_service.py` — HashiCorp Vault KV v2 integration for certificate private key storage
- `cluster_service.py` — Multi-cluster registry (bootstrap registration, API client factory for remote clusters)
- `access_request_service.py` — Just-in-time access workflow (request, approve, deny, revoke), automatic binding expiry, role eligibility policies
- `audit_service.py` — Query and export audit log entries

**Routers** (`backend/app/routers/`):
Each router maps to an OpenAPI tag (`auth`, `users`, `rbac`, `kubeconfig`, `tokens`, `cluster`, `access-requests`, `audit`, plus `vault_admin.py` under the `admin` tag) and provides REST endpoints for its domain, mounted under `/api/v1/...` in `main.py`. Routers delegate business logic to services and use FastAPI dependencies for authentication/authorization. There is no standalone "admin" router — ClusterVision login-account CRUD (list/create/delete/change role/reset password) lives under `routers/auth.py` (`/api/v1/auth/users/*`).

**Two separate "models" trees — do not confuse them:**
- `backend/app/models/` (`user.py`, `rbac.py`, `access_request.py`, `kubeconfig.py`, `audit.py`, `auth.py`) — Pydantic request/response schemas used by the routers.
- `backend/app/db/models.py` — SQLAlchemy ORM entities backed by PostgreSQL: `LocalUser`, `ManagedUser`, `AccessRequestRecord`, `TokenHistoryEntry`, `RegisteredCluster`, `VaultConfigRow`, `JitRolePolicy`, `AuditLogEntry`.

**Database** (`backend/app/db/`):
- `models.py` — the ORM entities above (all inherit a shared `Base`)
- `session.py` — engine/session factory (`new_session()`) and `init_db()`, which runs Alembic to head on startup

**Jobs** (`backend/app/jobs/`):
- `expire_access_bindings.py` — Standalone cleanup job (runs as Kubernetes CronJob) that deletes expired JIT-granted bindings across all registered clusters

### Frontend Structure

**Pages** (`frontend/src/pages/`):
Top-level route components wired up in `App.tsx`: `LoginPage`, `DashboardPage`, `UsersPage`, `RbacPage`, `KubeconfigPage`, `TokensPage`, `AccessRequestsPage`, `ClustersPage`, `AdminPage` (routed at `/settings`), `AuditLogPage`, `NotFoundPage`. All routes except `/login` are behind a `RequireAuth` route guard and share a common `Layout`.

**Components** (`frontend/src/components/`):
Organized by domain: `auth/`, `users/`, `rbac/`, `kubeconfig/`, `access/`, `admin/`, `clusters/`, `layout/`, `ui/` (shared UI primitives)

**API client** (`frontend/src/api/`):
- `client.ts` — Axios instance with automatic JWT refresh (401 → refresh token → retry), active cluster header injection, error formatting
- Other files — Typed API functions grouped by domain (auth, users, rbac, kubeconfig, tokens, vault, cluster, accessRequests, audit, admin)

**Hooks** (`frontend/src/hooks/`):
One `use<Domain>.ts` file per domain (e.g. `useUsers.ts`, `useRbac.ts`), wrapping the matching `api/` module in React Query (`@tanstack/react-query`) queries/mutations. Pages call these hooks rather than the `api/` functions directly.

**State management** (`frontend/src/store/`):
- `authStore.ts` — Zustand store for access token (in-memory only, never persisted)
- `clusterStore.ts` — Active cluster selection for multi-cluster operations

**Styling**: Tailwind CSS + custom components in `components/ui/`

## Key Implementation Details

### Authentication Flow
1. Local users (`source="local"`) have `password_hash` — authenticated via bcrypt comparison
2. LDAP users (`source="ldap"`) provisioned JIT on first successful bind — no local password, role derived from AD group membership on every login
3. JWT access tokens (15 min) + httpOnly refresh cookie (7 days). Access tokens never persisted — held in-memory in frontend state
4. Refresh flow: frontend intercepts 401, calls `/auth/refresh` with cookie, retries failed request with new token

### User Types
- **certificate**: X.509 client cert (CN=username, O=groups). Private keys generated in-memory, returned once, never stored server-side unless Vault enabled
- **service_account**: Kubernetes ServiceAccount + long-lived token Secret. ClusterVision creates both and tracks them in `managed_users` table

### Managed Resource Naming Convention
All ClusterVision-created bindings are named `clustervision-{username}-{role}` and labeled `managed-by: clustervision`. This prefix is used for cleanup (user deletion removes all matching bindings) and drift detection.

### Multi-Cluster Support
- Clusters registered via bootstrap script (short-lived token generated by admin, consumed by script that creates ServiceAccount + Secret in target cluster)
- Cluster credentials stored in `registered_clusters` table (`RegisteredCluster` model)
- All user/RBAC operations accept optional `?cluster=name` query param — backend uses stored credentials to target remote cluster
- JIT access cleanup job (`expire_access_bindings.py`) runs against all registered clusters + local cluster

### Just-In-Time Access (JIT)
- Users request time-boxed role grant → admin approves → ClusterVision creates binding with `clustervision.io/expires-at` annotation and `clustervision.io/jit=true` label
- Cleanup job (Kubernetes CronJob) deletes expired bindings across all clusters
- Admins can configure per-role eligibility policies via `JitRolePolicy` rows (block a role entirely or cap its max TTL below the global default)

### Vault Integration
When enabled (runtime config in Settings → Integrations), certificate private keys written to Vault KV v2 instead of returned inline. Vault config persisted in the `vault_config` table (`VaultConfigRow`, singleton row `id=1`), which takes precedence over Helm-supplied values.

### Audit Logging
`AuditLogMiddleware` logs every mutating request (POST/PUT/DELETE/PATCH) to the `audit_log` table (`AuditLogEntry`): actor, actor role, method + path, status code, and the redacted request payload. Admin-only export to CSV for compliance.

## Database Migrations

Use Alembic for schema changes. Migrations run automatically on pod startup (`alembic upgrade head` inside `init_db()`, called from the app lifespan).

**Creating a new migration:**
1. Modify models in `backend/app/db/models.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated file in `backend/alembic/versions/`
4. Test: `alembic upgrade head`

A database created by an old pre-Alembic release (plain `create_all()`, no `alembic_version` table) needs a one-time `alembic stamp 0001_initial_schema` before it can be upgraded — see README.md.

## Testing Conventions

Tests in `backend/tests/` use pytest and are service/core-layer unit tests — there are no FastAPI `TestClient`/router-level tests in this codebase. Key fixtures (in `conftest.py`):
- `db_session` — session bound to a shared in-memory SQLite engine (`StaticPool`, so all sessions in a test see the same data)
- `patch_new_session` (autouse) — points every service's module-level `new_session()` at that same in-memory database
- `reset_settings_cache` (autouse) — clears the `lru_cache`d `get_settings()` before/after each test so env-var changes don't leak between tests

Services that need a Kubernetes API client take `api_client=MagicMock()` (constructed per-test, not a fixture); tests then stub out the specific methods they exercise (see `test_access_request_service.py`).

Tests are auto-labeled with Allure features/severity in `conftest.py`'s `pytest_collection_modifyitems` (via `_FEATURE_BY_MODULE` / `_CRITICAL_MODULES` / `_SEVERITY_OVERRIDES`) rather than per-test decorators — update those maps, not individual test functions, when adding a new test module.

Run tests with `pytest` or `pytest --cov=app` for coverage.

## Common Patterns

**Adding a new service:**
1. Create `backend/app/services/new_service.py` with service class
2. Accept `api_client: client.ApiClient` and `db: Session` in constructor (for Kubernetes operations and database access)
3. If managing users, inherit from `RegistryMixin` (in `backend/app/core/registry.py`) and use `self._load_registry()` / `self._update_registry()`
4. Add router in `backend/app/routers/new_router.py`
5. Include router in `backend/app/main.py` with appropriate auth dependencies

**Adding a new frontend page:**
1. Create page component in `frontend/src/pages/NewPage.tsx`
2. Add route in `frontend/src/App.tsx`
3. Create API client functions in `frontend/src/api/new.ts`
4. Wrap them in a `frontend/src/hooks/useNew.ts` React Query hook and call that from the page
5. Add navigation link in `frontend/src/components/layout/Sidebar.tsx` (if needed)

## Environment Variables

**Backend** (see `backend/app/config.py` for full list):
- `DATABASE_URL` (required) — PostgreSQL connection string
- `APP_VERSION` — Version string (displayed in UI and OpenAPI)
- `CLUSTER_NAME` — Local cluster name (default: "kubernetes")
- `CLUSTER_API_URL` — Kubernetes API URL (auto-detected if empty)
- `CORS_ORIGINS` — JSON array or comma-separated list of allowed origins
- `PUBLIC_URL` — Canonical URL used in bootstrap scripts (auto-detected from request if empty)
- `LDAP_ENABLED`, `LDAP_URL`, `LDAP_BIND_DN`, `LDAP_BIND_PASSWORD`, etc. — LDAP configuration
- `VAULT_ENABLED`, `VAULT_ADDR`, `VAULT_TOKEN`, etc. — Vault configuration (can also be set at runtime via API)

**Frontend**: Vite proxies `/api` to `http://localhost:8000` in dev mode (see `vite.config.ts`). No frontend-specific env vars required.
