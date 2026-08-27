# PowerShell deployment script for ASTRA v0.4.1 to Google Cloud Run
param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    [string]$Region = "us-central1"
)

$ServiceName = "astra-investigation-service"
$ImageName = "gcr.io/$ProjectId/${ServiceName}:v0.4.1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Deploying ASTRA v0.4.1 (Google ADK + Gemini 3.5+) to Google Cloud Run" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId" -ForegroundColor Cyan
Write-Host "  Region:  $Region" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Build and push image
Write-Host "[1/3] Building container image via Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --project=$ProjectId --tag=$ImageName .

# 2. Deploy to Cloud Run
Write-Host "[2/3] Deploying service to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --project=$ProjectId `
    --image=$ImageName `
    --region=$Region `
    --platform="managed" `
    --allow-unauthenticated `
    --memory="1Gi" `
    --cpu="1" `
    --concurrency="80" `
    --timeout="60s" `
    --set-env-vars="ASTRA_OUTPUT_DIR=/tmp/artifacts,ASTRA_GEMINI_MODEL=gemini-2.5-flash"

# 3. Verify Health Check
$ServiceUrl = (gcloud run services describe $ServiceName --project=$ProjectId --region=$Region --format="value(status.url)")
Write-Host "[3/3] Verifying remote service via ASTRA cloud-verify at $ServiceUrl..." -ForegroundColor Yellow
python -m astra_poc cloud-verify --url $ServiceUrl

Write-Host "`nASTRA v0.4.1 is live at: $ServiceUrl" -ForegroundColor Green
Write-Host "Test agent endpoint: curl -X POST $ServiceUrl/agent/investigate -H 'Content-Type: application/json' -d '{\`"scenario\`": \`"hero\`", \`"seed\`": 42}'"
