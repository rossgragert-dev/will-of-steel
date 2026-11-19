# Non-destructive backup: copies one repo file to backups/<UTC timestamp>/<relative path>,
# verifies the SHA-256 of the copy matches, and appends a row to backups/BACKUP_LOG.md.
# Usage: powershell -File tools/backup-file.ps1 <relative-path> "<change description>"
# Never overwrites: fails if the destination already exists.
param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Change)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repo $Path
if (-not (Test-Path $src -PathType Leaf)) { throw "No such file: $src" }
$ts = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$dst = Join-Path $repo (Join-Path "backups\$ts" $Path)
if (Test-Path $dst) { throw "Backup already exists, refusing to overwrite: $dst" }
New-Item -ItemType Directory (Split-Path -Parent $dst) | Out-Null
Copy-Item -LiteralPath $src -Destination $dst
$h1 = (Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash
$h2 = (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash
if ($h1 -ne $h2) { throw "Checksum mismatch for backup of $Path" }
$null = Get-Content -LiteralPath $dst -TotalCount 1   # readability check
Add-Content -LiteralPath (Join-Path $repo 'backups\BACKUP_LOG.md') -Encoding utf8 -Value "| $ts | $Path | backups/$ts/$Path | $h1 | $Change |"
"BACKUP OK $Path -> backups/$ts/$Path ($h1)"
