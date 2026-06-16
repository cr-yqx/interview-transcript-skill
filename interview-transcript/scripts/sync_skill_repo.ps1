[CmdletBinding()]
param(
    [string]$SkillDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,
    [string]$GitPath = "git",
    [string]$CommitMessage = "Update interview transcript skill",
    [switch]$Push
)

$ErrorActionPreference = "Stop"

function Copy-PublicDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$TargetDir
    )

    if (-not (Test-Path -LiteralPath $SourceDir)) {
        return
    }

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    Get-ChildItem -LiteralPath $SourceDir -Recurse -File |
        Where-Object {
            $_.Name -notlike "*.pyc" -and
            $_.FullName -notmatch "\\__pycache__\\"
        } |
        ForEach-Object {
            $relative = $_.FullName.Substring($SourceDir.Length).TrimStart("\", "/")
            $destination = Join-Path $TargetDir $relative
            $destinationDir = Split-Path -Parent $destination
            New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
        }
}

$resolvedSkillDir = (Resolve-Path -LiteralPath $SkillDir).Path
$resolvedRepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$repoSkillDir = Join-Path $resolvedRepoRoot "interview-transcript"
$skillMd = Join-Path $resolvedSkillDir "SKILL.md"

if (-not (Test-Path -LiteralPath $skillMd)) {
    throw "SKILL.md not found: $skillMd"
}

$skillText = Get-Content -LiteralPath $skillMd -Raw -Encoding UTF8
if ($skillText -notmatch "(?s)^---\s*.*name:\s*interview-transcript\s+description:\s*.+?---") {
    throw "SKILL.md frontmatter is missing name or description."
}

New-Item -ItemType Directory -Force -Path $repoSkillDir | Out-Null
Copy-Item -LiteralPath $skillMd -Destination $repoSkillDir -Force
Copy-PublicDirectory -SourceDir (Join-Path $resolvedSkillDir "agents") -TargetDir (Join-Path $repoSkillDir "agents")
Copy-PublicDirectory -SourceDir (Join-Path $resolvedSkillDir "scripts") -TargetDir (Join-Path $repoSkillDir "scripts")
Copy-PublicDirectory -SourceDir (Join-Path $resolvedSkillDir "references") -TargetDir (Join-Path $repoSkillDir "references")

& $GitPath -C $resolvedRepoRoot add `
    ".gitignore" `
    "README.md" `
    "interview-transcript/SKILL.md" `
    "interview-transcript/agents" `
    "interview-transcript/scripts" `
    "interview-transcript/references"
if ($LASTEXITCODE -ne 0) {
    throw "git add failed"
}

& $GitPath -C $resolvedRepoRoot diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "No changes to commit."
    exit 0
}
if ($LASTEXITCODE -ne 1) {
    throw "git diff --cached failed"
}

& $GitPath -C $resolvedRepoRoot commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    throw "git commit failed"
}

if ($Push) {
    & $GitPath -C $resolvedRepoRoot push
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed"
    }
}
