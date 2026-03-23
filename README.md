# ClusterVision

Application de gestion des utilisateurs Kubernetes — création, droits RBAC et génération de kubeconfig.

## Fonctionnalités

- **Utilisateurs X.509** : création via l'API CSR Kubernetes, clé privée générée côté serveur et affichée une seule fois
- **ServiceAccounts** : création et gestion de token
- **RBAC** : visualisation des ClusterRoles/Roles, assignation et révocation par utilisateur
- **Kubeconfig** : génération et téléchargement du fichier de configuration kubectl

## Démarrage rapide (dev local)

```bash
# Prérequis : Docker, un kubeconfig valide dans ~/.kube/config

docker-compose up --build
# Frontend : http://localhost:3000
# Backend API : http://localhost:8000/docs
```

## Déploiement Kubernetes

```bash
# 1. Build des images
docker build -t clustervision-backend:latest ./backend
docker build -t clustervision-frontend:latest ./frontend

# 2. Appliquer les manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress.yaml
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
└── k8s/                  # Manifests Kubernetes
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
