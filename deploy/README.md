# Google Cloud Deployment Guide — ASTRA v0.4.1

This guide provides reproducible deployment steps for running the **ASTRA v0.4.1 Investigation Service** powered by **Google ADK** and **Gemini 3.5+** on **Google Cloud Run**.

---

## 1. Architecture Overview

```text
  [ Client / Judge CLI / HTTP Request ]
                    │
                    ▼
          [ Google Cloud Run ]
       (astra-investigation-service)
                    │
                    ▼
     [ Google ADK Investigation Agent ]
              (google-adk 2.8.0)
                    │
                    ▼
       [ Gemini 3.5+ Planning Agent ]
       (gemini-3.5-flash-lite / 3.7)
                    │
                    ▼
       [ ASTRA Restricted DSL Sandbox ]
         (DSLValidator + DSLExecutor)
                    │
                    ▼
    [ Telemetry / JSON Cloud Logging ]
```

---

## 2. Prerequisites

- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated.
- A GCP project with billing enabled:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  gcloud config set project YOUR_PROJECT_ID
  ```
- Enable required Google Cloud APIs:
  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com
  ```

---

## 3. One-Command Deployment

### Linux / macOS:
```bash
./deploy/deploy_cloud_run.sh YOUR_PROJECT_ID us-central1
```

### Windows PowerShell:
```powershell
.\deploy\deploy_cloud_run.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1
```

---

## 4. Direct Source Deployment via gcloud

```bash
gcloud run deploy astra-investigation-service \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60s \
    --set-env-vars ASTRA_OUTPUT_DIR=/tmp/artifacts,ASTRA_GEMINI_MODEL=gemini-3.5-flash-lite,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true
```

---

## 5. Gemini API Key Configuration (Optional Alternative to Vertex AI ADC)

To use a direct Gemini API key via Secret Manager instead of Vertex AI Workload Identity:

1. Store your Gemini API key in Secret Manager:
   ```bash
   echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
   ```
2. Grant Secret Accessor role to the Cloud Run service account:
   ```bash
   PROJECT_NUM=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
   gcloud secrets add-iam-policy-binding gemini-api-key \
       --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```
3. Update Cloud Run service with the secret:
   ```bash
   gcloud run services update astra-investigation-service \
       --region us-central1 \
       --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
       --set-env-vars ASTRA_GEMINI_MODEL=gemini-3.5-flash-lite
   ```

---

## 6. Remote Verification

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe astra-investigation-service --region us-central1 --format='value(status.url)')

# 1. Health check
curl -s "${SERVICE_URL}/health"

# 2. Remote agent investigation
curl -X POST "${SERVICE_URL}/agent/investigate" \
     -H "Content-Type: application/json" \
     -d '{"scenario": "hero", "seed": 42}'

# 3. Complete remote verification
python -m astra_poc cloud-verify --url "${SERVICE_URL}"
```
