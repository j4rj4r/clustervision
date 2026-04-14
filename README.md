# ClusterVision

A web UI for managing Kubernetes users, RBAC, and kubeconfig generation.

![Version](https://img.shields.io/github/v/tag/j4rj4r/clustervision?label=version)

## Features

- Create X.509 certificate users and ServiceAccounts
- Assign and revoke ClusterRoles and namespaced Roles
- Generate ready-to-use kubeconfig files
- Multi-cluster support

No external database — state lives in ConfigMaps and Secrets in the `clustervision` namespace.

## Installation

```bash
helm upgrade --install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --namespace clustervision --create-namespace \
  --set ingress.host=clustervision.example.com \
  --set backend.env.corsOrigins[0]=https://clustervision.example.com
```

For TLS and production configuration, see [`helm/clustervision/values.yaml`](helm/clustervision/values.yaml).

## Configuration

| Helm value | Default | Description |
|---|---|---|
| `ingress.host` | `clustervision.local` | Hostname |
| `ingress.className` | `traefik` | Ingress controller class |
| `backend.env.corsOrigins` | `[]` | Allowed CORS origins |
| `backend.env.publicUrl` | auto | Canonical URL used in bootstrap scripts |
| `networkPolicy.ingressControllerNamespace` | `traefik` | Ingress controller namespace |

## Security

Private keys for certificate users are generated in memory, shown once, and never stored. The backend runs with a minimal ClusterRole scoped to what ClusterVision actually needs.

ClusterVision has no built-in authentication — deploy it behind an auth proxy (OAuth2 Proxy, Authelia, etc.) and restrict access via VPN or IP allowlist.

## Development

**Backend** — Python 3.12 + FastAPI

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** — Node 20 + React + Vite

```bash
cd frontend
npm install
npm run dev
```

## License

MIT
