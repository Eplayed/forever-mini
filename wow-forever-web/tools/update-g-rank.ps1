<#
.SYNOPSIS
  一键从浏览器保存的 DD373 HTML（或手填区服比例）更新小程序「区服 G 排行」并发布到 OSS beta（无需重新发小程序版本）。

.EXAMPLE
  # 方式 1：自动读取 Downloads 里最新保存的 DD373 HTML 并发布
  .\wow-forever-web\tools\update-g-rank.ps1

  # 方式 2：指定多个保存的 HTML（如 PVP + 普通 + 角色扮演）
  .\wow-forever-web\tools\update-g-rank.ps1 -HtmlFiles "C:\Users\Administrator\Downloads\pvp.html","C:\Users\Administrator\Downloads\pve.html"

  # 方式 3：手填最新比例（最快，10 秒生效）
  .\wow-forever-web\tools\update-g-rank.ps1 -Set "PVP:部落:2.43","PVP:联盟:2.35"
#>
param(
  [string[]]$HtmlFiles = @(),
  [string[]]$Set = @(),
  [switch]$Merge,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $RepoRoot
try {

$pyArgs = @("-X", "utf8", "wow-forever-web/tools/import-g-rank.py")
if ($Merge) { $pyArgs += "--merge" }

if ($Set.Count -gt 0) {
  foreach ($s in $Set) { $pyArgs += @("--set", $s) }
} elseif ($HtmlFiles.Count -gt 0) {
  foreach ($f in $HtmlFiles) { $pyArgs += @("--html", $f) }
} else {
  $dl = Join-Path $env:USERPROFILE "Downloads"
  $latest = Get-ChildItem -Path $dl -Filter "*DD373*.html" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $latest) {
    Write-Error "未在 $dl 找到 *DD373*.html，请先在浏览器保存网页或使用 -Set 参数。"
    exit 1
  }
  Write-Host "使用最新保存文件：$($latest.FullName)" -ForegroundColor Cyan
  $pyArgs += @("--html", $latest.FullName)
}

& python @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Set-Location (Join-Path $RepoRoot "wow-forever-web")
& node tools/oss-release.js build --env beta --check-identity
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($DryRun) {
  Write-Host "DryRun 完成，未上传线上 OSS。" -ForegroundColor Yellow
  exit 0
}

$env:WOW_ALLOW_CROSS_CREDS = "1"
& node tools/oss-release.js upload --env beta
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& node tools/oss-release.js verify --env beta
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "区服 G 排行已发布至 OSS beta，约 1 分钟内小程序端自动生效（无需发版）。" -ForegroundColor Green
} finally {
  Pop-Location
}
