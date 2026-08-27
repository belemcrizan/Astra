# Google Cloud Deployment Guide — ASTRA v0.3

This guide provides reproducible deployment steps for running the **ASTRA v0.3 Investigation Service** on **Google Cloud Run**.

---

## 1. Architecture Overview

```text
  [ Client / Judge CLI / HTTP Request ]
                    |
                    v
          [ Google Cloud Run ]
      (astra-investigation-service)
                    |
          +---------+---------+
          |                   |
          v                   v
   [ Fast Investigation ]  [ Gemini API / Vertex AI ] (Optional)
    Deterministic Sandbox    Secret Manager / Env Var
          |
          v
   [ Telemetry / Report Artifacts ]
    Cloud Storage / Local Ephemeral
```

---

## 2. Prerequisites

- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated.
- A GCP project with billing enabled:
  ```bash
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```
- Enable required Google Cloud APIs:
  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
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

## 4. Manual Step-by-Step Deployment

### Step A: Build & Push Container Image
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/astra-investigation-service:v0.3.0 .
```

### Step B: Deploy to Cloud Run
```bash
gcloud run deploy astra-investigation-service \
    --image gcr.io/YOUR_PROJECT_ID/astra-investigation-service:v0.3.0 \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60s \
    --set-env-vars ASTRA_OUTPUT_DIR=/tmp/artifacts,ASTRA_USE_LLM=false
```

---

## 5. Optional: Enabling Google Gemini API Integration

To enable Gemini LLM structured investigation planning via Google Secret Manager:

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
       --set-env-vars ASTRA_USE_LLM=true,GEMINI_MODEL=gemini-2.5-flash
   ```

---

## 6. Verification & Remote Execution

Once deployed, verify the endpoints:

- **Health Check**:
  ```bash
  curl -s https://<SERVICE_URL>/health
  # Response: {"status":"healthy","service":"astra-investigation-service","version":"0.3.0","mode":"bounded-evidence-driven"}
  ```

- **Run Remote Judge Demo**:
  ```bash
  curl -s -X POST https://<SERVICE_URL>/judge-demo
  ```

- **Run Remote Real-World Dataset Investigation**:
  ```bash
  curl -s -X POST https://<SERVICE_URL>/real-demo
  ```

- **Retrieve Investigation Report Schema**:
  ```bash
  curl -s https://<SERVICE_URL>/schema
  ```
