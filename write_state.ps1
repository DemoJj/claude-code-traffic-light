param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("red", "green", "yellow")]
    [string]$State
)
# traffic_light_app
$projectDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
$project = Split-Path -Leaf $projectDir
$stateDir = Join-Path $env:USERPROFILE ".claude\traffic_light"
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
}
$stateFile = Join-Path $stateDir "$project.state"
Set-Content -Path $stateFile -Value $State -NoNewline
