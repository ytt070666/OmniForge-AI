param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status',
    [string]$RuntimeRoot = $env:OMNIAI_RUNTIME_ROOT
)

$ErrorActionPreference = 'Stop'
if (-not $RuntimeRoot) { throw 'Set OMNIAI_RUNTIME_ROOT or pass -RuntimeRoot' }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $RuntimeRoot 'omniai-training\Scripts\python.exe'
$script = Join-Path $projectRoot 'scripts\omnirag\phase3_visual_encoder_server.py'
$model = Join-Path $RuntimeRoot 'models\siglip2-base-patch16-384'
$tokenPath = if ($env:OMNIRAG_VISUAL_ENCODER_TOKEN_FILE) { $env:OMNIRAG_VISUAL_ENCODER_TOKEN_FILE } else { Join-Path $RuntimeRoot 'secrets\phase3_encoder_token.txt' }
$pidFile = Join-Path $projectRoot 'artifacts\runtime\ragflow\phase3_encoder_pid.txt'
$stdout = Join-Path $projectRoot 'artifacts\runtime\ragflow\phase3_encoder_stdout.log'
$stderr = Join-Path $projectRoot 'artifacts\runtime\ragflow\phase3_encoder_stderr.log'

function Get-EncoderProcess {
    if (-not (Test-Path -LiteralPath $pidFile)) { return $null }
    $serverPid = [int](Get-Content -LiteralPath $pidFile -Raw)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid" -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if ($process.ExecutablePath -ne $python -or $process.CommandLine -notlike "*$script*") {
        throw "PID $serverPid belongs to another process; refusing to manage it"
    }
    return $process
}

switch ($Action) {
    'status' {
        $process = Get-EncoderProcess
        if ($process) { Write-Output "encoder_running_pid=$($process.ProcessId)" }
        else { Write-Output 'encoder_stopped' }
    }
    'start' {
        if (Get-EncoderProcess) { Write-Output 'encoder_already_running'; break }
        if (Get-NetTCPConnection -LocalPort 11435 -State Listen -ErrorAction SilentlyContinue) {
            throw 'Port 11435 is already in use'
        }
        if (-not (Test-Path -LiteralPath $tokenPath)) { throw "Missing visual encoder token file: $tokenPath" }
        $env:OMNIRAG_VISUAL_ENCODER_TOKEN = [IO.File]::ReadAllText($tokenPath)
        $env:TEMP = Join-Path $RuntimeRoot 'tmp'
        $env:TMP = $env:TEMP
        $env:HF_HOME = Join-Path $RuntimeRoot 'hf-cache'
        $env:XDG_CACHE_HOME = $env:HF_HOME
        $env:TORCH_HOME = Join-Path $RuntimeRoot 'models'
        New-Item -ItemType Directory -Force -Path $env:TEMP, $env:HF_HOME | Out-Null
        $process = Start-Process -FilePath $python -ArgumentList @($script, '--model', $model, '--device', 'cuda') -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
        Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII
        for ($i = 0; $i -lt 30; $i++) {
            try {
                $health = Invoke-RestMethod -Uri 'http://127.0.0.1:11435/health' -TimeoutSec 2
                if ($health.status -eq 'ok') { Write-Output "encoder_ready_pid=$($process.Id)"; break }
            } catch { }
            Start-Sleep -Seconds 1
        }
        if (-not $health -or $health.status -ne 'ok') { throw 'Encoder did not become ready in 30 seconds' }
    }
    'stop' {
        $process = Get-EncoderProcess
        if ($process) { Stop-Process -Id $process.ProcessId; Write-Output "encoder_stopped_pid=$($process.ProcessId)" }
        if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile }
    }
}
