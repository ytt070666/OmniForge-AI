param(
    [string]$BaseUrl = 'http://127.0.0.1:9380/api/v1',
    [string]$SecretDir = $env:OMNIAI_SECRET_DIR
)

$ErrorActionPreference = 'Stop'
if (-not $SecretDir) {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $runtimeRoot = if ($env:OMNIAI_RUNTIME_ROOT) { $env:OMNIAI_RUNTIME_ROOT } else { Join-Path $projectRoot '.runtime' }
    $SecretDir = Join-Path $runtimeRoot 'secrets'
}
$secretPath = Join-Path $SecretDir 'ragflow_auth.json'

function Read-JsonResponse($response) {
    $body = $response.Content | ConvertFrom-Json
    if ($body.code -ne 0) { throw "RAGFlow API error $($body.code): $($body.message)" }
    return $body
}

function Encrypt-Password([string]$password) {
    $py = "import base64,sys; from Cryptodome.PublicKey import RSA; from Cryptodome.Cipher import PKCS1_v1_5; key=RSA.import_key(open('/ragflow/conf/public.pem','rb').read()); payload=base64.b64encode(sys.stdin.buffer.read().strip()); print(base64.b64encode(PKCS1_v1_5.new(key).encrypt(payload)).decode())"
    $encrypted = $password | docker exec -i docker-ragflow-cpu-1 python -c $py
    if ($LASTEXITCODE -ne 0 -or -not $encrypted) { throw 'Password encryption failed in RAGFlow container' }
    return $encrypted.Trim()
}

New-Item -ItemType Directory -Path $SecretDir -Force | Out-Null
if (Test-Path -LiteralPath $secretPath) {
    $auth = Get-Content -LiteralPath $secretPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $auth = [pscustomobject]@{
        email = 'omniai-gate1-20260930@localhost.local'
        password = [Convert]::ToBase64String($bytes)
        api_key = ''
    }
    $auth | ConvertTo-Json | Set-Content -LiteralPath $secretPath -Encoding UTF8
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$body = @{ email = $auth.email; password = (Encrypt-Password $auth.password) }
$loginResponse = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/auth/login" -Method Post -WebSession $session -ContentType 'application/json' -Body ($body | ConvertTo-Json -Compress)
$login = $loginResponse.Content | ConvertFrom-Json
if ($login.code -ne 0) {
    $registration = @{ nickname = 'OmniAI Gate1 Local'; email = $auth.email; password = $body.password }
    $response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/users" -Method Post -WebSession $session -ContentType 'application/json' -Body ($registration | ConvertTo-Json -Compress)
    Read-JsonResponse $response | Out-Null
    Write-Output 'LOCAL_ACCOUNT=created'
} else { Write-Output 'LOCAL_ACCOUNT=existing' }

if (-not $auth.api_key) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/system/tokens" -Method Post -WebSession $session -ContentType 'application/json' -Body '{}'
    $token = (Read-JsonResponse $response).data.token
    if (-not $token) { throw 'RAGFlow did not return an API key' }
    $auth.api_key = $token
    $auth | ConvertTo-Json | Set-Content -LiteralPath $secretPath -Encoding UTF8
}
Write-Output 'LOCAL_API_KEY=available'
Write-Output "SECRET_PATH=$secretPath"
