param(
    [string]$BaseUrl = 'http://127.0.0.1:9380/api/v1',
    [string]$SecretPath = $env:OMNIAI_RAGFLOW_AUTH_FILE,
    [string]$Model = 'omniai-vl-2b:8k',
    [string]$Instance = 'omniai-gate3-vl-8k-local'
)

$ErrorActionPreference = 'Stop'
if (-not $SecretPath) {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $runtimeRoot = if ($env:OMNIAI_RUNTIME_ROOT) { $env:OMNIAI_RUNTIME_ROOT } else { Join-Path $projectRoot '.runtime' }
    $SecretPath = Join-Path $runtimeRoot 'secrets\ragflow_auth.json'
}
if ($env:OMNIAI_RUNTIME_ROOT) {
    $env:TEMP = Join-Path $env:OMNIAI_RUNTIME_ROOT 'tmp'
    $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
}
$auth = Get-Content -LiteralPath $SecretPath -Raw -Encoding UTF8 | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $($auth.api_key)" }

function Call-Api([string]$method, [string]$path, $payload = $null) {
    $args = @{ Uri = "$BaseUrl/$path"; Method = $method; Headers = $headers; TimeoutSec = 180; UseBasicParsing = $true }
    if ($null -ne $payload) {
        $args.ContentType = 'application/json'
        $args.Body = ConvertTo-Json -InputObject $payload -Depth 12 -Compress
    }
    $result = Invoke-RestMethod @args
    if ($result.code -ne 0) { throw "RAGFlow $method $path failed: $($result.message)" }
    return $result
}

$instances = (Call-Api 'Get' 'providers/Ollama/instances').data
if (-not ($instances | Where-Object { $_.instance_name -eq $Instance })) {
    $payload = @{
        instance_name = $Instance
        api_key = ''
        base_url = 'http://host.docker.internal:11434'
        region = ''
        model_info = @(@{ model_name = $Model; model_type = @('chat', 'vision'); max_tokens = 8192; extra = @{} })
    }
    Call-Api 'Post' 'providers/Ollama/instances' $payload | Out-Null
    Write-Output 'VISION_INSTANCE=created_and_verified'
} else { Write-Output 'VISION_INSTANCE=existing' }

$tenant = (Call-Api 'Get' 'users/me/models').data
$modelId = "${Model}@${Instance}@Ollama"
$payload = @{
    tenant_id = $tenant.tenant_id
    llm_id = $modelId
    embd_id = $tenant.embd_id
    asr_id = $tenant.asr_id
    img2txt_id = $modelId
}
Call-Api 'Patch' 'users/me/models' $payload | Out-Null
$updated = (Call-Api 'Get' 'users/me/models').data
if ($updated.llm_id -ne $modelId -or $updated.img2txt_id -ne $modelId) { throw 'Vision defaults did not persist' }
Write-Output "DEFAULT_CHAT_AND_VISION=$Model"
