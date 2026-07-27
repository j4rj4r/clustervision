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
- **Just-in-time access** — self-service, time-boxed role requests with admin approval and automatic expiry

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

One of `database.url` or `database.existingSecret` is required — the chart fails at template time otherwise, and the backend won't start without `DATABASE_URL` set. Schema creation is automatic on startup (a plain `create_all`, no separate migration step to run).

Bring your own PostgreSQL instance — this chart does not deploy one. Native Kubernetes objects ClusterVision manages (RBAC objects, CSRs, ServiceAccount token Secrets) are not affected by this database and remain in Kubernetes as real cluster resources.

> **Precedence** — the runtime configuration is persisted in the `clustervision-vault-config` Secret and takes priority over Helm values. Once Vault has been configured (or disabled) from the UI, later `helm upgrade` changes to `vault.*` are ignored. To hand control back to Helm, delete that Secret:
> `kubectl delete secret clustervision-vault-config -n <namespace>`

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
