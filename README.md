# ClusterVision

Application de gestion des utilisateurs Kubernetes — création, droits RBAC et génération de kubeconfig.

## Fonctionnalités

- **Utilisateurs X.509** : création via l'API CSR Kubernetes, clé privée générée côté serveur et affichée une seule fois
- **ServiceAccounts** : création et gestion de token
- **RBAC** : visualisation des ClusterRoles/Roles, assignation et révocation par utilisateur
- **Kubeconfig** : génération et téléchargement du fichier de configuration kubectl

## Déploiement avec Helm

```bash
helm install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --version 1.0.0 \
  --namespace clustervision --create-namespace \
  --set ingress.host=clustervision.example.com
```

### Valeurs personnalisables

```yaml
# values-prod.yaml
backend:
  env:
    clusterName: "mon-cluster"

ingress:
  host: clustervision.example.com
  className: nginx
  tls:
    - secretName: clustervision-tls
      hosts:
        - clustervision.example.com
```

```bash
helm install clustervision oci://ghcr.io/j4rj4r/charts/clustervision \
  --version 1.0.0 \
  --namespace clustervision --create-namespace \
  -f values-prod.yaml
```

## Architecture

```
clustervision/
├── backend/              # FastAPI + kubernetes Python client
│   └── app/
│       ├── core/         # K8s client factory, exceptions
│       ├── models/       # Schémas Pydantic
│       ├── services/     # Logique métier (cert, SA, RBAC, kubeconfig)
│       └── routers/      # Endpoints REST
├── frontend/             # React + Vite + TailwindCSS
│   └── src/
│       ├── api/          # Clients HTTP
│       ├── hooks/        # React Query hooks
│       ├── components/   # UI components
│       └── pages/        # Pages
└── helm/clustervision/   # Helm chart
```

## Variables d'environnement (backend)

| Variable | Défaut | Description |
|---|---|---|
| `CLUSTER_NAME` | `kubernetes` | Nom du cluster dans le kubeconfig généré |
| `CLUSTER_API_URL` | auto | URL de l'API server (auto-détecté en in-cluster) |
| `REGISTRY_NAMESPACE` | `clustervision` | Namespace pour le ConfigMap registre utilisateurs |

## Sécurité

- La clé privée des utilisateurs certificat n'est **jamais stockée** côté serveur
- Elle est affichée une seule fois à la création et doit être sauvegardée par l'utilisateur
- Pour générer un kubeconfig, l'utilisateur doit fournir sa clé privée
- Le backend utilise un ServiceAccount Kubernetes dédié avec des droits RBAC minimaux
