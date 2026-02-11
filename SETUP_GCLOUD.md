# Setup Google Cloud - Integraciones

## Arquitectura
- **Cloud Run Jobs**: Ejecuta `run.py` como job batch (no 24/7)
- **Cloud Scheduler**: Programa ejecuciones cada hora
- **Secret Manager**: Almacena credenciales de forma segura
- **Artifact Registry**: Almacena imágenes Docker

## Pasos de configuración inicial (una sola vez)

### 1. Configurar proyecto en GCloud

```bash
# Autenticarse
gcloud auth login

# Seleccionar proyecto
gcloud config set project TU_PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  iam.googleapis.com
```

### 2. Crear repositorio en Artifact Registry

```bash
gcloud artifacts repositories create integraciones \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images para Integraciones"
```

### 3. Crear secretos en Secret Manager

```bash
# Crear cada secreto (te pedirá ingresar el valor)
echo -n "TU_DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=-
echo -n "TU_API_KEY" | gcloud secrets create API_KEY --data-file=-
echo -n "TU_SECRET_KEY" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "TU_UBIBOT_ACCOUNT_KEY" | gcloud secrets create UBIBOT_ACCOUNT_KEY --data-file=-
echo -n "TU_SENDGRID_API_KEY" | gcloud secrets create SENDGRID_API_KEY --data-file=-
```

### 4. Configurar Workload Identity Federation (para GitHub Actions)

```bash
# Crear pool de identidades
gcloud iam workload-identity-pools create "github-pool" \
  --project="TU_PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Crear provider para GitHub
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="TU_PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Crear service account para deploy
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# Asignar roles necesarios
PROJECT_ID=$(gcloud config get-value project)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Permitir que GitHub Actions use el service account
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/Empresas-Donar/Integraciones"
```

### 5. Configurar secretos en GitHub

En tu repositorio GitHub → Settings → Secrets and variables → Actions:

| Secret | Valor |
|--------|-------|
| `GCP_PROJECT_ID` | Tu ID de proyecto de GCloud |
| `WIF_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `github-actions-sa@PROJECT_ID.iam.gserviceaccount.com` |

Para obtener el PROJECT_NUMBER:
```bash
gcloud projects describe TU_PROJECT_ID --format='value(projectNumber)'
```

### 6. Configurar Cloud Scheduler (para ejecución automática cada hora)

```bash
# Crear scheduler que ejecute el job cada hora
gcloud scheduler jobs create http integraciones-hourly \
  --location=us-central1 \
  --schedule="0 * * * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/TU_PROJECT_ID/jobs/integraciones-job-staging:run" \
  --http-method=POST \
  --oauth-service-account-email="github-actions-sa@TU_PROJECT_ID.iam.gserviceaccount.com"
```

## Flujo de trabajo

1. Push a `feat/google-cloud-integration` → Deploy a `integraciones-job-staging`
2. Cuando todo funcione, cambiar el workflow para deploy desde `main`
3. Cambiar `JOB_NAME` a `integraciones-job` para producción

## Migrar a main

Cuando el staging funcione correctamente:

1. Editar `.github/workflows/deploy-cloud-run.yml`:
   - Descomentar `- main` en branches
   - Cambiar `JOB_NAME` a `integraciones-job` (sin -staging)

2. Crear nuevo Cloud Scheduler para producción apuntando al job de producción

## Costos estimados

| Servicio | Costo mensual estimado |
|----------|----------------------|
| Cloud Run Jobs | $0-5 (solo paga por ejecución) |
| Artifact Registry | ~$0.10/GB |
| Secret Manager | ~$0.06/secret |
| Cloud Scheduler | Gratis (primeros 3 jobs) |
| **Total** | **~$1-5/mes** |

## Comandos útiles

```bash
# Ver logs del job
gcloud run jobs executions list --job=integraciones-job-staging --region=us-central1

# Ejecutar job manualmente
gcloud run jobs execute integraciones-job-staging --region=us-central1

# Ver logs de una ejecución específica
gcloud run jobs executions logs EXECUTION_NAME --region=us-central1
```
