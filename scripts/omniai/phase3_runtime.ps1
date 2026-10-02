param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status',
    [string]$VerifierOverride = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runtimeRoot = if ($env:OMNIAI_RUNTIME_ROOT) { $env:OMNIAI_RUNTIME_ROOT } else { Join-Path $root '.runtime' }
$env:TEMP = Join-Path $runtimeRoot 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$index = Join-Path $root 'artifacts\omnirag\visual_index_ragflow_siglip2.jsonl'
$tokenPath = if ($env:OMNIRAG_VISUAL_ENCODER_TOKEN_FILE) { $env:OMNIRAG_VISUAL_ENCODER_TOKEN_FILE } else { Join-Path $runtimeRoot 'secrets\phase3_encoder_token.txt' }
$encoder = Join-Path $PSScriptRoot 'phase3_encoder.ps1'
$compose = @(
    '-f', 'docker/docker-compose.yml',
    '-f', 'infra/omniai/ragflow-minimal.override.yml',
    '-f', 'infra/omniai/ragflow-phase2.override.yml',
    '-f', 'infra/omniai/ragflow-phase3.override.yml'
)
if ($VerifierOverride) {
    $resolvedOverride = (Resolve-Path -LiteralPath $VerifierOverride).Path
    $compose += @('-f', $resolvedOverride)
}
$compose += @('--profile', 'cpu', '--profile', 'elasticsearch', '--profile', 'metadata-mysql')

Set-Location -LiteralPath $root
if ($Action -ne 'status') {
    if (-not (Test-Path -LiteralPath $tokenPath)) { throw "Missing visual encoder token file: $tokenPath" }
    $env:OMNIRAG_VISUAL_ENCODER_TOKEN = [IO.File]::ReadAllText($tokenPath)
    $env:EXPOSE_MYSQL_PORT = '13306'
}

switch ($Action) {
    'start' {
        if (-not (Test-Path -LiteralPath $index)) { throw "Build the real RAGFlow visual index first: $index" }
        & $encoder start -RuntimeRoot $runtimeRoot
        docker start omniai-gate1-ollama | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Ollama container failed to start' }
        docker compose @compose up -d mysql es01 redis minio ragflow-cpu
        if ($LASTEXITCODE -ne 0) { throw 'RAGFlow Phase-3 Compose failed to start' }
    }
    'stop' {
        docker compose @compose stop ragflow-cpu es01 mysql minio redis
        if ($LASTEXITCODE -ne 0) { throw 'RAGFlow Phase-3 Compose failed to stop' }
        docker stop omniai-gate1-ollama | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Ollama container failed to stop' }
        & $encoder stop -RuntimeRoot $runtimeRoot
    }
    'status' {
        & $encoder status -RuntimeRoot $runtimeRoot
        docker ps --filter name=docker-ragflow-cpu-1 --filter name=omniai-gate1-ollama --format '{{.Names}} {{.Status}}'
    }
}
