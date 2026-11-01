#!/usr/bin/env bash
# Parity on Cloud Run (spec §12). Idempotent: every step may be re-run.
#
#   deploy/cloudrun.sh setup     enable APIs, Artifact Registry repo, bucket, service account, secret shell
#   deploy/cloudrun.sh secret    store MODEL_API_KEY (from $MODEL_API_KEY, else .env) as a new secret version  <- run this yourself
#   deploy/cloudrun.sh build     Cloud Build → Artifact Registry (tag = git sha)
#   deploy/cloudrun.sh deploy    gcloud run deploy with the spec's flags; prints the URL
#   deploy/cloudrun.sh url       print the service URL
#   deploy/cloudrun.sh teardown  delete the service, image repo, bucket, secret and service account
#
# Needs: gcloud signed in, a project with billing, `gcloud config set project ...`. Docker is not needed.
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-parity}"
REPO="${REPO:-parity}"
BUCKET="${BUCKET:-${PROJECT}-parity-runs}"
SA_NAME="${SA_NAME:-parity-run}"
SA="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
SECRET="${SECRET:-parity-model-api-key}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/parity"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

say() { printf '\n== %s\n' "$*"; }
need_project() { [ -n "$PROJECT" ] || { echo "no project: gcloud config set project <id>"; exit 1; }; }

setup() {
  need_project
  say "APIs"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com --project "$PROJECT"
  say "Artifact Registry repo $REPO"
  gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud artifacts repositories create "$REPO" --repository-format docker --location "$REGION" --project "$PROJECT" --description "Parity images"
  say "Bucket gs://$BUCKET (uniform access, never public)"
  gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" --uniform-bucket-level-access --public-access-prevention
  say "Service account $SA"
  gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT" --display-name "Parity Cloud Run runtime"
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member "serviceAccount:$SA" --role roles/storage.objectAdmin --project "$PROJECT" >/dev/null
  say "Secret $SECRET (shell; add the value with: deploy/cloudrun.sh secret)"
  gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1 \
    || gcloud secrets create "$SECRET" --replication-policy automatic --project "$PROJECT"
  gcloud secrets add-iam-policy-binding "$SECRET" --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor --project "$PROJECT" >/dev/null
  say "setup complete"
}

secret() {
  need_project
  local key="${MODEL_API_KEY:-}"
  if [ -z "$key" ] && [ -f "$ROOT/.env" ]; then
    key="$(grep -E '^MODEL_API_KEY=' "$ROOT/.env" | head -1 | cut -d= -f2- | tr -d '"'"'" | tr -d '[:space:]')"
  fi
  [ -n "$key" ] || { echo "MODEL_API_KEY not found in the environment or .env"; exit 1; }
  printf '%s' "$key" | gcloud secrets versions add "$SECRET" --data-file=- --project "$PROJECT" >/dev/null
  say "secret $SECRET has a new version (the value was not printed)"
}

build() {
  need_project
  say "Cloud Build → $IMAGE:$TAG"
  gcloud builds submit "$ROOT" --tag "$IMAGE:$TAG" --project "$PROJECT" --region "$REGION" --timeout 1800
}

deploy() {
  need_project
  say "Cloud Run deploy $SERVICE ($IMAGE:$TAG)"
  gcloud run deploy "$SERVICE" --image "$IMAGE:$TAG" --project "$PROJECT" --region "$REGION" --platform managed \
    --allow-unauthenticated --execution-environment gen2 \
    --min-instances 1 --max-instances 1 --cpu 2 --memory 2Gi --no-cpu-throttling --timeout 3600 --concurrency 20 \
    --service-account "$SA" \
    --set-secrets "MODEL_API_KEY=${SECRET}:latest" \
    --set-env-vars "PARITY_GCS_BUCKET=${BUCKET},PARITY_INDEX_PATH=/tmp/index.db,PARITY_CACHE_DIR=/tmp/cache,PARITY_DEFAULT_MODE=replay,PARITY_TRUST_PROXY=1,LOG_LEVEL=info"
  url
}

url() { gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format 'value(status.url)'; }

teardown() {
  need_project
  gcloud run services delete "$SERVICE" --project "$PROJECT" --region "$REGION" --quiet || true
  gcloud artifacts repositories delete "$REPO" --location "$REGION" --project "$PROJECT" --quiet || true
  gcloud storage rm -r "gs://$BUCKET" --project "$PROJECT" || true
  gcloud secrets delete "$SECRET" --project "$PROJECT" --quiet || true
  gcloud iam service-accounts delete "$SA" --project "$PROJECT" --quiet || true
}

case "${1:-}" in
  setup|secret|build|deploy|url|teardown) "$1" ;;
  all) setup; if [ -n "${MODEL_API_KEY:-}" ] || [ -f "$ROOT/.env" ]; then secret; else echo "no MODEL_API_KEY: run 'deploy/cloudrun.sh secret' before deploy"; fi; build; deploy ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
