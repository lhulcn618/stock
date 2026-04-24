$ErrorActionPreference = "Stop"

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envScript = Join-Path $rootDir "scripts\windows-tauri-env.cmd"
$distIndex = Join-Path $rootDir "dist\index.html"
$sourceExe = Join-Path $rootDir "target-rustlld-serial\release\stock-watch-desktop.exe"
$outDir = Join-Path $rootDir "builds"
$latestExe = Join-Path $outDir "stock-watch-desktop-latest.exe"
$srcFiles = @(
  (Join-Path $rootDir "src\App.tsx"),
  (Join-Path $rootDir "src\styles.css")
)

function Invoke-Step {
  param(
    [string]$Label,
    [string]$Command
  )

  Write-Host $Label
  & $envScript cmd /c $Command
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

Invoke-Step "[1/4] Building frontend assets..." "npm run build"

if (-not (Test-Path -LiteralPath $distIndex)) {
  throw "Missing dist\index.html after frontend build."
}

$distTime = (Get-Item -LiteralPath $distIndex).LastWriteTimeUtc
$latestSrcTime = ($srcFiles | ForEach-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc } | Sort-Object -Descending | Select-Object -First 1)
if ($distTime -lt $latestSrcTime) {
  throw "Frontend dist is stale. dist\index.html is older than src assets."
}

Invoke-Step "[2/4] Building Tauri release executable..." "npx tauri build --no-bundle"

if (-not (Test-Path -LiteralPath $sourceExe)) {
  throw "Missing target executable after Tauri build."
}

$exeTime = (Get-Item -LiteralPath $sourceExe).LastWriteTimeUtc
if ($exeTime -lt $distTime) {
  throw "Built executable is stale. target exe is older than dist assets."
}

if (-not (Test-Path -LiteralPath $outDir)) {
  New-Item -ItemType Directory -Path $outDir | Out-Null
}

Write-Host "[3/4] Copying latest executable..."
Copy-Item -LiteralPath $sourceExe -Destination $latestExe -Force

$buildStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stampedExe = Join-Path $outDir "stock-watch-desktop-$buildStamp.exe"

Write-Host "[4/4] Creating timestamped executable..."
Copy-Item -LiteralPath $sourceExe -Destination $stampedExe -Force

Write-Host "EXE_READY=$latestExe"
Write-Host "EXE_ARCHIVE=$stampedExe"
