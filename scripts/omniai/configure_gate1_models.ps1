param(
    [string]$BaseUrl = 'http://127.0.0.1:9380/api/v1',
    [string]$SecretPath = $env:OMNIAI_RAGFLOW_AUTH_FILE
)

$ErrorActionPreference = 'Stop'
if (-not $SecretPath) {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $runtimeRoot = if ($env:OMNIAI_RUNTIME_ROOT) { $env:OMNIAI_RUNTIME_ROOT } else { Join-Path $projectRoot '.runtime' }
    $SecretPath = Join-Path $runtimeRoot 'secrets\ragflow_auth.json'
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

$providers = (Call-Api 'Get' 'providers?available=false').data
if (-not ($providers | Where-Object { $_.name -eq 'Ollama' -or $_.provider_name -eq 'Ollama' })) {
    Call-Api 'Put' 'providers' @{ provider_name = 'Ollama' } | Out-Null
    Write-Output 'OLLAMA_PROVIDER=created'
} else { Write-Output 'OLLAMA_PROVIDER=existing' }

$instances = (Call-Api 'Get' 'providers/Ollama/instances').data
if (-not ($instances | Where-Object { $_.instance_name -eq 'omniai-gate1-local' })) {
    $models = @(
        @{ model_name = 'qwen3:0.6b'; model_type = @('chat'); max_tokens = 4096; extra = @{} },
        @{ model_name = 'qwen3-embedding:0.6b'; model_type = @('embedding'); max_tokens = 8192; extra = @{} }
    )
    $payload = @{
        instance_name = 'omniai-gate1-local'
        api_key = ''
        base_url = 'http://host.docker.internal:11434'
        region = ''
        model_info = $models
    }
    Call-Api 'Post' 'providers/Ollama/instances' $payload | Out-Null
    Write-Output 'OLLAMA_INSTANCE=created_and_verified'
} else { Write-Output 'OLLAMA_INSTANCE=existing' }

$tenant = (Call-Api 'Get' 'users/me/models').data
$llm = 'qwen3:0.6b@omniai-gate1-local@Ollama'
$embedding = 'qwen3-embedding:0.6b@omniai-gate1-local@Ollama'
$payload = @{
    tenant_id = $tenant.tenant_id
    llm_id = $llm
    embd_id = $embedding
    asr_id = $tenant.asr_id
    img2txt_id = $tenant.img2txt_id
}
Call-Api 'Patch' 'users/me/models' $payload | Out-Null
$updated = (Call-Api 'Get' 'users/me/models').data
if ($updated.llm_id -ne $llm -or $updated.embd_id -ne $embedding) { throw 'Default model settings did not persist' }
Write-Output 'DEFAULT_CHAT=qwen3:0.6b'
Write-Output 'DEFAULT_EMBEDDING=qwen3-embedding:0.6b'
