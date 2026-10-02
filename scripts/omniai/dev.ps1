param(
    [ValidateSet('validate','gateway','agent','vector','langchain','llamaindex','tensorflow','distributed','polyglot','omniops','test','status')]
    [string]$Command = 'status'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runtimeRoot = if ($env:OMNIAI_RUNTIME_ROOT) { $env:OMNIAI_RUNTIME_ROOT } else { Join-Path $root '.runtime' }
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
$runtimeRoot = (Resolve-Path -LiteralPath $runtimeRoot).Path
$env:TEMP = Join-Path $runtimeRoot 'tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $runtimeRoot 'pip-cache'
New-Item -ItemType Directory -Force -Path $env:TEMP, $env:PIP_CACHE_DIR | Out-Null
Set-Location -LiteralPath $root
$env:PYTHONPATH = $root
$env:OMNIOPS_MODE = if ($env:OMNIOPS_MODE) { $env:OMNIOPS_MODE } else { 'demo' }
$goBin = if ($env:OMNIAI_GO_BIN) { $env:OMNIAI_GO_BIN } else { Join-Path $runtimeRoot 'go\bin' }
if (Test-Path -LiteralPath (Join-Path $goBin 'gofmt.exe')) { $env:PATH = "$goBin;$env:PATH" }

function Python-For([string]$name) {
    $directory = if ($name -eq 'gateway') { 'omniai-gateway-venv' } else { "omniai-$name" }
    $path = Join-Path $runtimeRoot "$directory\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $path)) { throw "缺少 $name 环境：$path" }
    return $path
}

function Run-Checked([string]$program, [string[]]$arguments) {
    # Windows PowerShell 5 turns native stderr warnings into terminating errors
    # when ErrorActionPreference is Stop. The process exit code is authoritative.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $program @arguments 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message }
            else { $_ }
        }
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($code -ne 0) { throw "$program 退出码 $code" }
}

function TensorFlow-Python {
    $path = if ($env:OMNIAI_TF_PYTHON) { $env:OMNIAI_TF_PYTHON } else { Join-Path $runtimeRoot 'omniai-tf\Scripts\python.exe' }
    if (-not (Test-Path -LiteralPath $path)) { throw "缺少 TensorFlow 环境：$path；可用 OMNIAI_TF_PYTHON 指定" }
    return $path
}

switch ($Command) {
    'validate' {
        $py = Python-For 'gateway'
        Run-Checked $py @('scripts/omniai/validate_platform.py')
        Run-Checked $py @('scripts/omnirag/phase8_final_acceptance.py')
        Run-Checked $py @('scripts/omnirag/omniops_selfcheck.py')
    }
    'gateway' {
        $py = Python-For 'gateway'
        Run-Checked $py @('scripts/omnirag/run_omniops.py')
    }
    'omniops' {
        $py = Python-For 'gateway'
        Run-Checked $py @('scripts/omnirag/run_omniops.py')
    }
    'agent' {
        $py = Python-For 'agent'
        Run-Checked $py @('-m','uvicorn','services.omniai_agent.app:app','--host','127.0.0.1','--port','8091')
    }
    'vector' {
        $py = Python-For 'vector'
        Run-Checked $py @('scripts/omniai/smoke_vector.py')
        docker version --format '{{.Server.Version}}' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop Linux daemon 未运行' }
        docker run --rm -v "${root}:/work" -w /work python:3.13-slim sh -c 'PIP_ROOT_USER_ACTION=ignore pip install -q --disable-pip-version-check -i https://pypi.tuna.tsinghua.edu.cn/simple -r labs/vector_lab/requirements.txt && python labs/vector_lab/milvus_lite_demo.py'
        if ($LASTEXITCODE -ne 0) { throw 'Milvus Lite 容器验证失败' }
    }
    'langchain' {
        Run-Checked (Python-For 'langchain') @('labs/langchain_lab/runnable_demo.py')
    }
    'llamaindex' {
        Run-Checked (Python-For 'llamaindex') @('-m','uvicorn','services.omniai_llamaindex.app:app','--host','127.0.0.1','--port','8094')
    }
    'tensorflow' {
        Run-Checked (TensorFlow-Python) @('-m','uvicorn','services.omniai_tensorflow.app:app','--host','127.0.0.1','--port','8095')
    }
    'distributed' {
        if (-not (Get-NetTCPConnection -LocalPort 4222 -State Listen -ErrorAction SilentlyContinue)) {
            docker compose -f infra/omniai/docker-compose.yml --profile distributed up -d nats
            if ($LASTEXITCODE -ne 0) { throw 'NATS 启动失败' }
        }
        Run-Checked (Python-For 'gateway') @('scripts/omniai/smoke_distributed.py')
    }
    'polyglot' {
        Run-Checked (Python-For 'gateway') @('scripts/omniai/smoke_polyglot.py')
    }
    'test' {
        Run-Checked (Python-For 'gateway') @('scripts/omniai/validate_platform.py')
        Run-Checked (Python-For 'gateway') @('scripts/omniai/smoke_gateway_contract.py')
        Run-Checked (Python-For 'gateway') @('scripts/omniai/smoke_concurrency.py')
        Run-Checked (Python-For 'agent') @('scripts/omniai/smoke_agent.py')
        Run-Checked (Python-For 'agent') @('scripts/omniai/smoke_optional_contract.py','agent')
        Run-Checked (Python-For 'langchain') @('labs/langchain_lab/runnable_demo.py')
        Run-Checked (Python-For 'llamaindex') @('scripts/omniai/smoke_llamaindex.py')
        Run-Checked (Python-For 'llamaindex') @('scripts/omniai/smoke_optional_contract.py','llamaindex')
        Run-Checked (TensorFlow-Python) @('scripts/omniai/smoke_tensorflow.py')
        Run-Checked (TensorFlow-Python) @('scripts/omniai/smoke_optional_contract.py','tensorflow')
        Run-Checked (Python-For 'agent') @('scripts/omniai/smoke_mcp.py')
        Run-Checked (Python-For 'agent') @('scripts/omniai/smoke_integrated.py')
        Run-Checked (Python-For 'gateway') @('scripts/omniai/smoke_polyglot.py')
    }
    'status' {
        foreach ($name in @('gateway','agent','langchain','llamaindex','vector','training','load')) {
            $directory = if ($name -eq 'gateway') { 'omniai-gateway-venv' } else { "omniai-$name" }
            $path = Join-Path $runtimeRoot "$directory\Scripts\python.exe"
            Write-Output "$name : $(if (Test-Path -LiteralPath $path) { 'installed' } else { 'missing' })"
        }
        Write-Output "tensorflow : $(if (Test-Path -LiteralPath (TensorFlow-Python)) { 'installed' } else { 'missing' })"
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $dockerVersion = & docker version --format 'Docker: {{.Server.Version}}' 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Output $dockerVersion }
            else { Write-Output 'Docker: unavailable' }
        }
        finally { $ErrorActionPreference = $previousPreference }
        Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalPort -in @(4222,8090,8091,8092,8093,8094,8095,8096,9090) } |
            Select-Object LocalPort,OwningProcess
        $global:LASTEXITCODE = 0
    }
}
