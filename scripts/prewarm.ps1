<#
.SYNOPSIS
    Pre-warm the Render backend before a demo: wake it up, then run one real
    scan so the lazy-loaded RapidOCR ONNX engine (backend/lmd/cv/pipeline_a.py
    _get_engine, lru_cache(maxsize=1)) is loaded and its slow first-inference
    cost is already paid before a judge watches.

.PARAMETER BaseUrl
    Backend root URL, e.g. https://lmd-backend.onrender.com. Defaults to the
    local dev server.

.PARAMETER Image
    Path to a demo image to scan. Defaults to one of the repo's research
    sample images.

.PARAMETER TimeoutSeconds
    How long to keep polling /health before giving up.

.EXAMPLE
    .\scripts\prewarm.ps1 -BaseUrl https://lmd-backend.onrender.com
#>
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Image = "research\mainResearch\02_flat_box_clean.jpg",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

# POST /api/v1/scans is unauthenticated (backend/lmd/api/scan.py) -- only
# case creation/advancement needs the inspector bearer token -- so no auth
# headers are needed for this warm-up scan.

Write-Host "Waking $BaseUrl ..."
$start = Get-Date
$awake = $false
while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSeconds) {
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/health" -TimeoutSec 5 -UseBasicParsing
        if ($resp.StatusCode -eq 200) {
            $awake = $true
            break
        }
    } catch {
        # still asleep / cold-starting -- keep polling
    }
    Start-Sleep -Seconds 3
}

$elapsed = ((Get-Date) - $start).TotalSeconds
if (-not $awake) {
    Write-Error "Backend did not respond within $TimeoutSeconds s."
    exit 1
}
Write-Host ("Backend awake after {0:N1}s" -f $elapsed)

$imagePath = Resolve-Path $Image
Write-Host "Running warm-up scan on $imagePath ..."

$scanStart = Get-Date
$form = @{
    image = Get-Item -Path $imagePath
}
$result = Invoke-RestMethod -Uri "$BaseUrl/api/v1/scans" -Method Post -Form $form -TimeoutSec 180
$scanElapsed = ((Get-Date) - $scanStart).TotalSeconds

Write-Host ("Scan complete in {0:N1}s -- verdict: {1}" -f $scanElapsed, $result.overall_verdict)
Write-Host "Backend is warm. Subsequent scans should be significantly faster."
