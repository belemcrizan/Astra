#!/usr/bin/env bash
set -euo pipefail

# ASTRA v0.4.1 — Google Cloud Run Deployment Script
# Usage: ./deploy_cloud_run.sh <PROJECT_ID> [REGION]

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${2:-us-central1}"
SERVICE_NAME="astra-investigation-service"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v0.4.1"

if [[ -z "$PROJECT_ID" ]]; then
    echo "ERROR: Project ID is required. Pass as argument or set GOOGLE_CLOUD_PROJECT."
    echo "Usage: ./deploy_cloud_run.sh <PROJECT_ID> [REGION]"
    exit 1
fi

echo "=========================================================="
echo "  Deploying ASTRA v0.4.1 (Google ADK + Gemini 3.5+) to Google Cloud Run"
echo "  Project: ${PROJECT_ID}"
echo "  Region:  ${REGION}"
echo "  Service: ${SERVICE_NAME}"
echo "=========================================================="

# 1. Build and push container image using Cloud Build
echo "[1/3] Building container image via Google Cloud Build..."
gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_NAME}" .

# 2. Deploy to Cloud Run
echo "[2/3] Deploying service to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --image="${IMAGE_NAME}" \
    --region="${REGION}" \
    --platform="managed" \
    --allow-unauthenticated \
    --memory="1Gi" \
    --cpu="1" \
    --concurrency="80" \
    --timeout="60s" \
    --set-env-vars="ASTRA_OUTPUT_DIR=/tmp/artifacts,ASTRA_GEMINI_MODEL=gemini-2.5-flash"

# 3. Verify health endpoint
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')
echo "[3/3] Verifying remote service via ASTRA cloud-verify at ${SERVICE_URL}..."
python -m astra_poc cloud-verify --url "${SERVICE_URL}"

echo ""
echo "ASTRA v0.4.1 is live at: ${SERVICE_URL}"
echo "Test agent investigation: curl -X POST ${SERVICE_URL}/agent/investigate -H 'Content-Type: application/json' -d '{\"scenario\": \"hero\", \"seed\": 42}'"
