# ClusterVision

A web UI for managing Kubernetes users, RBAC permissions, and kubeconfig generation.

![Version](https://img.shields.io/github/v/tag/j4rj4r/clustervision?label=version)

## Features

- **User management** — create X.509 certificate users and ServiceAccounts; import existing ones
- **RBAC management** — ClusterRoles, namespaced Roles, bindings, access simulator
- **Kubeconfig generation** — ready-to-use files for `kubectl`, with audit trail
- **Multi-cluster** — manage multiple clusters from a single instance; add them with a generated bootstrap script or manually (connectivity is verified at registration)
- **JWT authentication** — admin/viewer roles, 15-min access tokens, 7-day httpOnly refresh cookie
- **Vault integration** — store certificate private keys in HashiCorp Vault KV v2
- **Just-in-time access** — self-service, time-boxed role requests with admin approval and automatic expiry; admins can block specific roles from self-service entirely or cap their max TTL below the global default
- **LDAP / Active Directory login** — bind directly against on-prem AD, role derived from group membership, no ADFS or other broker required
- **Audit log** — every mutating request against RBAC, users, tokens, cluster registry and Vault config is recorded (actor, action, outcome), successful or denied
- **Compliance exports** — CSV export of the audit log and the access-request history (requester, approver, role, outcome), date-range filterable, for access-review evidence

Requires a PostgreSQL database — all ClusterVision application state (login accounts, managed user registry, token history, cluster registry, Vault runtime config, access requests) lives there. Native Kubernetes objects ClusterVision manages (RBAC objects, CSRs, ServiceAccount token Secrets) are unaffected and remain in Kubernetes.

## Installation

```bash
helm upgrade --install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --namespace clustervision --create-namespace \
  --set ingress.host=clustervision.example.com \
  --set backend.env.corsOrigins[0]=https://clustervision.example.com \
  --set backend.env.auth.adminPassword.value=changeme \
  --set backend.env.database.url=postgresql+psycopg://user:pass@host:5432/clustervision
```

For production configuration see [`helm/clustervision/values.yaml`](helm/clustervision/values.yaml).

## Configuration

### Core

| Helm value | Default | Description |
|---|---|---|
| `ingress.host` | `clustervision.local` | Public hostname |
| `ingress.className` | `traefik` | Ingress controller class |
| `backend.env.corsOrigins` | `[]` | Allowed CORS origins |
| `backend.env.publicUrl` | auto | Canonical URL used in bootstrap scripts |
| `networkPolicy.ingressControllerNamespace` | `traefik` | Ingress controller namespace |

### Authentication

| Helm value | Default | Description |
|---|---|---|
| `backend.env.auth.jwtSecret.value` | auto-generated | JWT signing secret (stable across upgrades via `lookup`) |
| `backend.env.auth.jwtSecret.existingSecret` | `""` | Use a pre-existing Kubernetes Secret |
| `backend.env.auth.adminPassword.value` | `""` | Initial admin password (applied once on first start) |
| `backend.env.auth.adminPassword.existingSecret` | `""` | Use a pre-existing Kubernetes Secret |
| `backend.env.auth.secureCookie` | `true` | Set `Secure` flag on the refresh cookie (disable for HTTP dev) |

### Vault integration (optional)

| Helm value | Default | Description |
|---|---|---|
| `vault.enabled` | `false` | Enable Vault integration |
| `vault.addr` | `""` | Vault server address (e.g. `https://vault.example.com`) |
| `vault.token` | `""` | Vault token (creates a managed Secret) |
| `vault.existingSecret` | `""` | Use a pre-existing Secret containing the token |
| `vault.existingSecretKey` | `token` | Key holding the token in that Secret |
| `vault.mount` | `secret` | KV v2 mount path |
| `vault.basePath` | `clustervision/users` | Base path for stored keys |
| `vault.namespace` | `""` | Vault Enterprise namespace |
| `vault.tlsSkipVerify` | `false` | Skip TLS certificate verification (self-signed Vault) |

`vault.enabled=true` requires `vault.token` or `vault.existingSecret` — the chart fails at template time otherwise.

Vault can also be configured at runtime from the Settings → Integrations panel (no restart required).

### Database (required)

| Helm value | Default | Description |
|---|---|---|
| `backend.env.database.url` | `""` | SQLAlchemy connection URL, e.g. `postgresql+psycopg://user:pass@host:5432/clustervision` (creates a managed Secret) |
| `backend.env.database.existingSecret` | `""` | Use a pre-existing Secret containing the URL |
| `backend.env.database.existingSecretKey` | `database-url` | Key holding the URL in that Secret |

One of `database.url` or `database.existingSecret` is required — the chart fails at template time otherwise, and the backend won't start without `DATABASE_URL` set.

Bring your own PostgreSQL instance — this chart does not deploy one. Native Kubernetes objects ClusterVision manages (RBAC objects, CSRs, ServiceAccount token Secrets) are not affected by this database and remain in Kubernetes as real cluster resources.

#### Schema migrations (Alembic)

Every pod runs `alembic upgrade head` on startup — safe to leave as-is on every deploy, a no-op once the database is already current.

> **One-time step if you deployed before this version** — earlier releases created the schema with a plain `create_all()` and never wrote an `alembic_version` table. Run `alembic upgrade head` against that database without preparing it first and it will fail (`relation "local_users" already exists"`), because Alembic assumes an empty database and tries to recreate tables that are already there. Before upgrading, tell Alembic the schema is already at the pre-LDAP baseline — this records the version, it does not touch any table or data:
> ```bash
> cd backend
> DATABASE_URL=postgresql+psycopg://user:pass@host:5432/clustervision \
>   alembic stamp 0001_initial_schema
> ```
> Run this once, from anywhere with network access to that database and the backend's Python environment (e.g. `kubectl exec` into a running backend pod, or locally with the same `DATABASE_URL`). After that, deploying the new version runs `alembic upgrade head` automatically and applies only what's actually new (currently: `local_users.source`, `local_users.last_login_at`, making `local_users.password_hash` nullable) — existing rows and accounts are preserved.

> **Precedence** — the runtime configuration is persisted in the `clustervision-vault-config` Secret and takes priority over Helm values. Once Vault has been configured (or disabled) from the UI, later `helm upgrade` changes to `vault.*` are ignored. To hand control back to Helm, delete that Secret:
> `kubectl delete secret clustervision-vault-config -n <namespace>`

### LDAP / Active Directory integration (optional)

| Helm value | Default | Description |
|---|---|---|
| `backend.env.ldap.enabled` | `false` | Enable LDAP login |
| `backend.env.ldap.url` | `""` | e.g. `ldaps://dc01.company.local:636` |
| `backend.env.ldap.bindDn` | `""` | Service account DN used to search for the user's DN |
| `backend.env.ldap.bindPassword` | `""` | Bind password (creates a managed Secret) |
| `backend.env.ldap.existingSecret` | `""` | Use a pre-existing Secret containing the bind password |
| `backend.env.ldap.existingSecretKey` | `bind-password` | Key holding the password in that Secret |
| `backend.env.ldap.userSearchBase` | `""` | e.g. `OU=Users,DC=company,DC=local` |
| `backend.env.ldap.userSearchFilter` | `(sAMAccountName={username})` | LDAP filter, `{username}` is substituted |
| `backend.env.ldap.adminGroupDn` | `""` | Members of this group DN get the `admin` role |
| `backend.env.ldap.viewerGroupDn` | `""` | Members get `viewer`; empty means any successful bind gets `viewer` |
| `backend.env.ldap.tlsSkipVerify` | `false` | Skip TLS certificate verification (self-signed AD CA) |

`ldap.enabled=true` requires `ldap.bindPassword` or `ldap.existingSecret` — the chart fails at template time otherwise.

This binds directly against on-premises Active Directory (LDAP/LDAPS) — no ADFS or other OIDC/SAML broker needed. Login is search-then-bind: ClusterVision binds as the service account to find the user's DN and group membership, then re-binds as the user with their password to verify credentials. The local login form is unchanged — no new page, no redirect flow. A local account (`source="local"`) always takes priority for its own username; everyone else is checked against LDAP if enabled.

Accounts are provisioned just-in-time on first successful login and re-validated against AD on every subsequent one — nothing is cached or trusted locally. Their role is re-derived from group membership every time, so a group change or a disabled AD account takes effect on the next login. LDAP-sourced accounts appear in Settings → Users with a `LDAP` badge; their password and role can't be edited there (managed in AD), and removing one only revokes access until they sign in again.

## Security

### Authentication & authorisation
- JWT access tokens (15 min), renewed via httpOnly `Secure; SameSite=Strict` refresh cookie (7 days)
- Two roles: `admin` (full access) and `viewer` (read-only)
- Tokens are in-memory only — never stored in `localStorage` or cookies

### Certificate private keys
- Generated in-memory, returned **once** in the API response, never persisted server-side
- When Vault is enabled, keys are written to Vault KV v2 and not returned in the response at all

### Kubernetes permissions
- Runs with a minimal ClusterRole scoped to exactly the API groups ClusterVision needs
- All managed resources are labeled `managed-by: clustervision` and named `clustervision-*`

### API docs
The Swagger UI (`/api/v1/docs`) and ReDoc (`/api/v1/redoc`) are enabled by default.
In production, restrict access to these paths at the ingress level if needed.

## API

Interactive docs available at `/api/v1/docs` (Swagger) and `/api/v1/redoc` (ReDoc).

Authenticate in Swagger: click **Authorize**, enter `Bearer <access_token>`.
Obtain a token via `POST /api/v1/auth/login`.

| Tag | Prefix | Auth |
|-----|--------|------|
| `auth` | `/api/v1/auth` | Public (login/refresh); admin for user CRUD |
| `users` | `/api/v1/users` | All authenticated |
| `rbac` | `/api/v1/rbac` | All authenticated (writes: admin) |
| `kubeconfig` | `/api/v1/kubeconfig` | All authenticated |
| `tokens` | `/api/v1/tokens` | All authenticated (writes: admin) |
| `cluster` | `/api/v1/cluster` | All authenticated |
| `admin` | `/api/v1/admin` | Admin only |
| `access-requests` | `/api/v1/access-requests` | All authenticated (approve/deny/revoke: admin) |
| `audit` | `/api/v1/audit` | Admin only |

## Development

**Backend** — Python 3.12 + FastAPI, requires a PostgreSQL database (e.g. `docker run -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16`)

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:dev@localhost:5432/postgres
uvicorn app.main:app --reload
```

**Frontend** — Node 20 + React + Vite

```bash
cd frontend
npm install
npm run dev
```

API runs on `:8000`, UI on `:5173`. CORS is pre-configured for local development.

## License

MIT
