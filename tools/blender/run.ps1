# Runs one Blender script headlessly with the project's safety settings.
# Usage: powershell -File tools/blender/run.ps1 <script.py> [args...]
# - --factory-startup: user preferences are neither read nor saved; autosave off.
# - TEMP/TMP are redirected (for this process only) into build/blender-temp inside the repo.
# - A new, uniquely named log is written to build/logs/.
param([Parameter(Mandatory)][string]$Script, [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# The Blender executable path is machine-specific: keep it in a git-ignored file, one line, full path to blender.exe.
$cfg = Join-Path $PSScriptRoot 'blender-path.local.txt'
if (-not (Test-Path $cfg)) { throw "Create $cfg containing the full path to blender.exe (this file is git-ignored)." }
$B = (Get-Content -LiteralPath $cfg -TotalCount 1).Trim()
$env:TEMP = Join-Path $repo 'build\blender-temp'; $env:TMP = $env:TEMP
$logs = Join-Path $repo 'build\logs'; if (-not (Test-Path $logs)) { New-Item -ItemType Directory $logs | Out-Null }
$name = [IO.Path]::GetFileNameWithoutExtension($Script)
$log = Join-Path $logs ("$name-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.log')
$scriptPath = if ([IO.Path]::IsPathRooted($Script)) { $Script } else { Join-Path $repo $Script }
& $B -b --factory-startup --python-exit-code 1 --python $scriptPath -- @Rest *> $log
$code = $LASTEXITCODE
Get-Content $log | Where-Object { $_ -match 'Traceback|Error|error:|WOS_|File ".*line' -and $_ -notmatch 'gpu.vulkan|NativeCommandError|CategoryInfo|FullyQualified' }
"EXIT $code  LOG $log"
