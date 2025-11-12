# ArgoCD Deployment for MALA Language Learning Platform

This directory contains ArgoCD Application manifests for deploying the MALA language learning platform with Supabase branch preview support.

## Features

- **GitOps Deployment**: Automatic sync from Git repository
- **Feature Branch Previews**: Automatic deployment of feature branches
- **Supabase Branch Preview Integration**: Each feature branch gets its own Supabase preview database
- **Auto-sync**: Changes pushed to Git are automatically deployed
- **Self-healing**: Automatic recovery from configuration drift

---

## Prerequisites

1. **k3s Cluster** running
2. **ArgoCD** installed
3. **Supabase CLI** for branch management
4. **GitHub Token** for PR-based previews
5. **Container Registry** (Docker Hub, GitHub Registry, etc.)

---

## Installation

### 1. Install ArgoCD on k3s

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 2. Access ArgoCD UI

```bash
# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Login
argocd login localhost:8080 --username admin --password <password-from-step-1>
```

### 3. Setup GitHub Token for PR Previews

```bash
# Create GitHub token secret
kubectl create secret generic github-token \
  --from-literal=token=<your-github-token> \
  -n argocd
```

### 4. Deploy Main Application

```bash
kubectl apply -f application.yaml
```

### 5. Deploy ApplicationSet for Feature Branches

```bash
kubectl apply -f applicationset-branches.yaml
```

---

## Supabase Branch Preview Integration

### Setup Supabase Branch Previews

1. **Install Supabase CLI**:
```bash
npm install -g supabase
```

2. **Link your project**:
```bash
cd language-learning-platform/services/django-backend
supabase link --project-ref <your-project-ref>
```

3. **Create branch preview script** (`.github/workflows/preview.yml`):
```yaml
name: Deploy Preview

on:
  pull_request:
    types: [opened, synchronize]
    branches:
      - 'claude/**'

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create Supabase Preview Branch
        run: |
          supabase branches create pr-${{ github.event.pull_request.number }} \
            --project-ref ${{ secrets.SUPABASE_PROJECT_REF }}

      - name: Get Preview DB URL
        id: preview
        run: |
          PREVIEW_URL=$(supabase branches get pr-${{ github.event.pull_request.number }} --format json | jq -r '.database_url')
          echo "database_url=$PREVIEW_URL" >> $GITHUB_OUTPUT

      - name: Create K8s Secret for Preview
        run: |
          kubectl create secret generic supabase-pr-${{ github.event.pull_request.number }} \
            --from-literal=database_url=${{ steps.preview.outputs.database_url }} \
            -n argocd --dry-run=client -o yaml | kubectl apply -f -

      - name: Trigger ArgoCD Sync
        run: |
          argocd app sync mala-${{ github.head_ref }}-${{ github.event.pull_request.number }}
```

4. **Run migrations on preview branch**:
```bash
# Connect to preview branch
export DATABASE_URL=<preview-database-url>

# Run migrations
cd services/django-backend
python manage.py migrate
python manage.py loaddata fixtures/*
```

---

## Feature Branch Deployment Workflow

### 1. Create Feature Branch
```bash
git checkout -b claude/add-new-feature-<session-id>
# Make changes
git commit -m "feat: add new feature"
git push origin claude/add-new-feature-<session-id>
```

### 2. Automatic Deployment
ArgoCD will automatically:
1. Detect the new branch
2. Create a new namespace: `language-learning-<branch-name>`
3. Deploy all services to the new namespace
4. Create Supabase preview database
5. Run migrations
6. Expose services

### 3. Access Preview Environment
```bash
# Get service URLs
kubectl get ingress -n language-learning-claude-add-new-feature-<session-id>

# Or port-forward
kubectl port-forward -n language-learning-<branch> svc/django-backend 8000:8000
kubectl port-forward -n language-learning-<branch> svc/bun-api 3001:3001
```

### 4. Test Feature
```bash
# Access API
curl http://localhost:8000/api/v1/languages/

# Access Swagger docs
open http://localhost:8000/api/docs/
```

### 5. Cleanup After Merge
```bash
# Delete preview branch in Supabase
supabase branches delete pr-<number>

# ArgoCD will automatically cleanup the namespace
```

---

## Configuration

### Environment Variables per Branch

ArgoCD ApplicationSet automatically injects environment variables:

- `SUPABASE_URL`: Preview branch URL
- `DATABASE_URL`: Preview database URL
- `BRANCH_NAME`: Git branch name
- `PR_NUMBER`: Pull request number

### Custom Kustomize Overlays

Create custom overlays for specific branches:

```bash
mkdir -p k8s/overlays/claude-add-podcast-feature

# Copy from dev overlay
cp -r k8s/overlays/dev/* k8s/overlays/claude-add-podcast-feature/

# Customize kustomization.yaml
```

---

## Monitoring

### View Application Status

```bash
# List all applications
argocd app list

# Get specific app status
argocd app get mala-language-learning

# View sync status
argocd app sync-status mala-language-learning
```

### View Logs

```bash
# View Django logs
kubectl logs -f deployment/django-backend -n language-learning

# View Pipecat logs
kubectl logs -f deployment/pipecat-service -n language-learning

# View Celery worker logs
kubectl logs -f deployment/celery-worker -n language-learning
```

### Health Checks

```bash
# Check application health
argocd app wait mala-language-learning --health

# Check all pods
kubectl get pods -n language-learning
```

---

## Troubleshooting

### Application Not Syncing

```bash
# Force sync
argocd app sync mala-language-learning --force

# Check sync errors
argocd app get mala-language-learning --show-operation
```

### Database Migrations Failing

```bash
# Manually run migrations
kubectl exec -it deployment/django-backend -n language-learning -- python manage.py migrate

# Check migration status
kubectl exec -it deployment/django-backend -n language-learning -- python manage.py showmigrations
```

### Supabase Preview Branch Issues

```bash
# List preview branches
supabase branches list

# Get branch details
supabase branches get pr-<number> --format json

# Delete and recreate
supabase branches delete pr-<number>
supabase branches create pr-<number>
```

---

## Best Practices

1. **Always use feature branches** starting with `claude/`
2. **Test locally first** with docker-compose
3. **Run migrations** before deploying
4. **Monitor logs** during deployment
5. **Cleanup old branches** regularly
6. **Use descriptive branch names** with session IDs
7. **Tag releases** in Git for production deployments

---

## CI/CD Pipeline

### GitHub Actions Integration

See `.github/workflows/` for:
- `preview.yml`: Deploy feature branch previews
- `production.yml`: Deploy to production
- `cleanup.yml`: Cleanup old previews

### Image Building

```bash
# Build and push images
cd services/django-backend
docker build -t <registry>/mala-django:${BRANCH_NAME} .
docker push <registry>/mala-django:${BRANCH_NAME}
```

---

## Production Deployment

### 1. Create Production Application

```bash
kubectl apply -f application-prod.yaml
```

### 2. Configure Production Secrets

```bash
kubectl create secret generic mala-secrets \
  --from-literal=database-url=<prod-db-url> \
  --from-literal=gemini-api-key=<key> \
  -n language-learning
```

### 3. Deploy

```bash
argocd app sync mala-production
```

---

## Support

For issues:
- Check ArgoCD UI: http://localhost:8080
- View logs: `kubectl logs -n argocd deployment/argocd-application-controller`
- ArgoCD docs: https://argo-cd.readthedocs.io/
- Supabase branching: https://supabase.com/docs/guides/platform/branching
