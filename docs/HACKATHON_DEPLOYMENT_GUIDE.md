# ASTRA v0.4.1 — Google Hackathon Deployment Guide

This guide describes the **mandatory Google technology stack** used by ASTRA for the hackathon submission:

```text
Gemini 3.5+
    +
Google Agent Development Kit (ADK)
    +
Google Cloud Run
```

ASTRA's scientific core remains deterministic and bounded.

Gemini and Google ADK provide the autonomous investigation-planning layer, while ASTRA retains authority over tool validation, numerical execution, evidence updates, stopping policy, and final investigation decisions.

---

# 1. Mandatory Hackathon Architecture

```text
Client / Judge / HTTP Request
            │
            ▼
      Google Cloud Run (FastAPI Backend)
            │
            ▼
 Google ADK Investigation Agent (google-adk 2.8.0)
            │
            ▼
       Gemini 3.5+ (gemini-3.5-flash-lite / gemini-3.7-flash)
            │
     Structured Proposal (InvestigationProposal)
            │
            ▼
     ASTRA Tool Boundary (Bounded Diagnostic Tools)
            │
            ▼
      Restricted DSL Sandbox
            │
            ▼
      DSL Validator
            │
      ┌─────┴─────┐
      │           │
    Reject      Execute
                  │
                  ▼
       Deterministic ASTRA Core
        /        │         \
      VoI   Falsification  H_unknown
        \        │         /
             Stop Policy
                  │
                  ▼
       CLOSE / WATCH / DEFER /
              ESCALATE
                  │
                  ▼
      Provenance + Audit Trail (SHA-256 Chaining)
```

---

# 2. Responsibility Boundaries

## Google ADK
Google ADK orchestrates the agent lifecycle and exposes ASTRA's bounded tools to Gemini.

## Gemini 3.5+
Gemini participates in:
- investigation planning
- candidate diagnostic selection
- hypothesis discrimination planning
- multimodal evidence interpretation when enabled

Gemini does **NOT**:
- execute arbitrary Python
- directly modify hypothesis scores
- override ASTRA governance
- change preregistered thresholds
- directly create verified evidence
- execute external interventions

## ASTRA
ASTRA remains responsible for:
- restricted DSL validation
- budget enforcement
- deterministic statistical execution
- evidence verification
- hypothesis updating
- falsification
- Value-of-Information policy
- open-set handling
- stopping decisions
- audit provenance

---

# 3. Prerequisites

Install the current Google Cloud CLI and authenticate:

```powershell
gcloud auth login
gcloud auth application-default login
```

Select the Google Cloud project:

```powershell
gcloud config set project YOUR_PROJECT_ID
```

Verify:

```powershell
gcloud config get-value project
```

---

# 4. Enable Required Google Cloud APIs

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  aiplatform.googleapis.com
```

If Secret Manager is used:

```powershell
gcloud services enable secretmanager.googleapis.com
```

---

# 5. Local Python Environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
```

Verify installation:

```powershell
python -m pip show astra-poc
python -m pip show google-adk
python -m pip show google-genai
```

---

# 6. Gemini 3.5+ Configuration

ASTRA uses Gemini 3.5 or newer (`gemini-3.5-flash-lite`, `gemini-3.7-flash`):

```powershell
$env:ASTRA_GEMINI_MODEL="gemini-3.5-flash-lite"
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
$env:GOOGLE_GENAI_USE_VERTEXAI="true"
```

If using a Gemini API key:

```powershell
$env:GEMINI_API_KEY="your-gemini-api-key"
```

---

# 7. Local Verification Commands

```powershell
# 1. Audit mandatory eligibility stack
python -m astra_poc eligibility-check

# 2. Run live Google ADK + Gemini 3.5+ agent demo
python -m astra_poc google-agent-demo

# 3. Run live Google API integration test
python -m astra_poc integration-test-google

# 4. Run complete automated unit test suite (77 tests passing)
python -m unittest discover -s tests -v
```

---

# 8. Google Cloud Run Deployment

Deploy directly from source:

```powershell
gcloud run deploy astra-investigation-service `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 1Gi `
  --cpu 1 `
  --timeout 60s `
  --set-env-vars ASTRA_GEMINI_MODEL=gemini-3.5-flash-lite,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true
```

Or deploy using the PowerShell script:

```powershell
.\deploy\deploy_cloud_run.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1
```

---

# 9. Remote Verification on Cloud Run

Retrieve and verify the live service URL:

```powershell
$ASTRA_URL = gcloud run services describe astra-investigation-service --region us-central1 --format="value(status.url)"
$ASTRA_URL

# Remote Cloud Verification
python -m astra_poc cloud-verify --url $ASTRA_URL
```

Invoke remote agent endpoint:

```powershell
$body = @{
    scenario = "hero"
    seed = 42
    max_turns = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "$ASTRA_URL/agent/investigate" `
  -ContentType "application/json" `
  -Body $body
```

---

# 10. Live Video Demonstration Script Reference

See [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for the exact 3:30 video timing, narration, and screen actions including Google Cloud Console, active revisions, and live log inspection.
