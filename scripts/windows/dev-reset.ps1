# Ageless Pipeline – Developer Reset (PowerShell)
# Run from the repo root (folder containing .git)

$ErrorActionPreference = "Stop"

function Say($msg){ Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor Cyan }

# 1) Ensure we're in a git repo
if (-not (Test-Path ".git")) { throw "Not a git repo. Open a terminal in the repo root." }

# 2) Go to main and sync
Say "Checking out main…"
git checkout main | Out-Null
Say "Fetching and pulling origin/main…"
git fetch origin | Out-Null
git pull origin main | Out-Null

# 3) Delete local branches except main (force only if fully merged)
Say "Deleting local feature branches…"
$branches = (git branch --format="%(refname:short)") -split "`n"
foreach ($b in $branches) {
  $name = $b.Trim()
  if ($name -and $name -ne "main") {
    try {
      git branch -d $name | Out-Null    # -d = delete if merged
    } catch {
      Write-Host "Skip (not merged): $name" -ForegroundColor Yellow
    }
  }
}

# 4) Clean caches / outputs / logs
Say "Cleaning pipeline outputs…"
$paths = @(
  "pipeline\output\json", "pipeline\output\txt", "pipeline\output\csv", "pipeline\output\batches",
  "pipeline\logs",
  "Scans_Error"
)
foreach ($p in $paths) {
  if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
  New-Item -ItemType Directory -Force -Path $p | Out-Null
  # restore .gitkeep where relevant
  $gk = Join-Path $p ".gitkeep"
  if (-not (Test-Path $gk)) { "" | Out-File $gk -Encoding utf8 }
}

Say "Removing Python __pycache__…"
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

Say "Clearing Electron UI runtime cache (if present)…"
$ui = "AgelessPipelineUI"
if (Test-Path "$ui\Cache")     { Remove-Item "$ui\Cache" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "$ui\UserData")  { Remove-Item "$ui\UserData" -Recurse -Force -ErrorAction SilentlyContinue }

Say "Deleting loose *.log files…"
Get-ChildItem -Path . -Recurse -Include *.log -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# 5) Final status
Say "Done."
git status
