# ClusterVision

A web UI for managing Kubernetes users, RBAC, and kubeconfig generation — without `kubectl`.

![Version](https://img.shields.io/github/v/tag/j4rj4r/clustervision?label=version)

---

## Features

| Feature | Description |
|---|---|
| **X.509 Users** | Create certificate-based users via the Kubernetes CSR API. Private key is generated server-side, shown once, and never stored. |
| **ServiceAccounts** | Create and manage ServiceAccounts and their tokens. |
| **RBAC** | Browse ClusterRoles and namespace Roles. Assign or revoke permissions per user. |
| **Kubeconfig** | Generate and download a ready-to-use `kubectl` config file. |
| **Multi-Cluster** | Connect additional clusters and manage permissions across all of them from a single interface. |

---

## Architecture

```
clustervision/
├── backend/              # FastAPI + kubernetes Python client
│   └── app/
│       ├── core/         # K8s client factory, exception handlers
│       ├── models/       # Pydantic schemas
│       ├── services/     # Business logic (cert, SA, RBAC, kubeconfig, clusters)
│       └── routers/      # REST endpoints (/users, /rbac, /kubeconfig, /cluster)
├── frontend/             # React 18 + TypeScript + Vite + Tailwind CSS
│   └── src/
│       ├── api/          # Axios HTTP clients
│       ├── hooks/        # React Query data-fetching hooks
│       ├── store/        # Zustand global state (active cluster)
│       ├── components/   # Reusable UI components
│       └── pages/        # UsersPage, RbacPage, KubeconfigPage, ClustersPage
└── helm/clustervision/   # Helm chart for Kubernetes deployment
```

The backend runs as a Kubernetes Pod with a dedicated ServiceAccount. It talks to the Kubernetes API directly using the in-cluster config. No external database — all state (user registry, cluster registry) lives in ConfigMaps and Secrets inside the `clustervision` namespace.

---

## Quick Start

### Deploy with Helm

```bash
helm install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --version 1.2.3 \
  --namespace clustervision --create-namespace \
  --set ingress.host=clustervision.example.com
```

Then open `http://clustervision.example.com` in your browser.

### Production values

```yaml
# values-prod.yaml
backend:
  env:
    clusterName: "my-cluster"
    corsOrigins: ["https://clustervision.example.com"]

ingress:
  host: clustervision.example.com
  className: nginx          # or traefik, haproxy, etc.
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  tls:
    - secretName: clustervision-tls
      hosts:
        - clustervision.example.com

networkPolicy:
  enabled: true
  ingressControllerNamespace: ingress-nginx   # adjust to your setup
```

```bash
helm install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --version 1.2.3 \
  --namespace clustervision --create-namespace \
  -f values-prod.yaml
```

---

## Configuration

### Backend environment variables

| Variable | Default | Description |
|---|---|---|
| `CLUSTER_NAME` | `kubernetes` | Name used in generated kubeconfig files |
| `CLUSTER_API_URL` | *(auto)* | Kubernetes API server URL — auto-detected in-cluster |
| `REGISTRY_NAMESPACE` | `clustervision` | Namespace for the user registry ConfigMap |
| `REGISTRY_CONFIGMAP` | `user-registry` | ConfigMap name for the user registry |
| `CLUSTERS_SECRET` | `clustervision-clusters` | Secret name for the multi-cluster registry |
| `CORS_ORIGINS` | `[]` | Allowed CORS origins (JSON array or comma-separated list) |

### Helm values reference

| Path | Default | Description |
|---|---|---|
| `backend.replicaCount` | `1` | Backend replicas |
| `frontend.replicaCount` | `1` | Frontend replicas |
| `ingress.className` | `traefik` | Ingress controller class |
| `ingress.host` | `clustervision.local` | Hostname |
| `ingress.tls` | `[]` | TLS configuration (see above) |
| `networkPolicy.enabled` | `true` | Restrict pod ingress to ingress controller only |
| `networkPolicy.ingressControllerNamespace` | `traefik` | Ingress controller namespace for network policy |

---

## Multi-Cluster

Add remote clusters from the **Clusters** page by providing a name and a kubeconfig. ClusterVision stores the remote cluster credentials in a Kubernetes Secret (`clustervision-clusters`) and lets you switch context from the top bar.

---

## Security Notes

- **Private keys are never stored.** For X.509 users, the key is generated in memory, shown once, and then discarded. The user must save it.
- **Kubeconfig generation requires the private key.** The user must provide it at generation time — the backend never holds it beyond the request.
- **The backend runs with minimal RBAC.** The Helm chart creates a ClusterRole scoped to only what ClusterVision needs (CSR management, RBAC reads/writes, ConfigMaps, Secrets in its namespace).
- **Network Policy** restricts inbound traffic to the ingress controller pod only.
- **No authentication layer is included.** ClusterVision is designed to be deployed behind your existing access control (VPN, SSO proxy, IP allowlist). See [Production Checklist](#production-checklist) below.

---

## Production Checklist

ClusterVision does not include its own authentication. Before exposing it, make sure the following are covered:

- [ ] **Authentication proxy** in front of the ingress (e.g. OAuth2 Proxy, Authelia, Pomerium, Keycloak Gatekeeper)
- [ ] **TLS** enabled on the ingress (`ingress.tls` in Helm values)
- [ ] **CORS** restricted to your frontend hostname (`backend.env.corsOrigins`)
- [ ] **Network Policy** enabled and scoped to your ingress controller namespace
- [ ] **Access limited** to trusted operators (VPN, IP allowlist, or SSO group)
- [ ] **Audit log** — enable Kubernetes API audit logging to track what ClusterVision does on the cluster
- [ ] **Backup** of the `user-registry` ConfigMap (user metadata) and `clustervision-clusters` Secret (multi-cluster credentials)

---

## Development

### Prerequisites

- Node.js 20+
- Python 3.12+
- A running Kubernetes cluster (local or remote) with `kubectl` configured

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # starts on http://localhost:3000, proxies /api to localhost:8000
```

### Build Docker images locally

```bash
docker build -t clustervision-backend ./backend
docker build --build-arg VITE_APP_VERSION=dev -t clustervision-frontend ./frontend
```

---

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| **Build & Push Images** | Push to `main`, version tags, PRs | Builds multi-platform images (amd64 + arm64) and pushes to `ghcr.io` |
| **Helm Release** | Version tags (`v*.*.*`) | Lints, packages and publishes the Helm chart to `oci://ghcr.io/j4rj4r/charts/clustervision`, creates a GitHub Release with changelog |

Images are tagged with the semver version, a short SHA, and `latest` (on `main`).

---

## License

MIT
