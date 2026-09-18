[CmdletBinding()]
param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "storage\.runtime"
$PidFile = Join-Path $RuntimeDir "processes.json"
$AppUrl = "http://localhost:3000"
$HealthUrl = "http://127.0.0.1:8000/api/health"

$FrontendPort = 3000
$BackendPort = 8000

function Test-AppPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $connection.Wait(1500)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Stop-AppProcesses {
    if (-not (Test-Path $PidFile)) {
        Write-Host "No processes started by start_app.bat were found."
        return
    }

    $record = Get-Content -Raw $PidFile | ConvertFrom-Json
    $managedProcesses = @(
        @{ process_id = $record.frontend_pid; command_pattern = "standalone.server\.js" },
        @{ process_id = $record.backend_pid; command_pattern = "backend\.app\.main:app" }
    )
    foreach ($managedProcess in $managedProcesses) {
        $processId = $managedProcess.process_id
        if (-not $processId) {
            continue
        }
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($process -and $process.CommandLine -match $managedProcess.command_pattern) {
            & taskkill.exe /PID $processId /T /F 2>$null | Out-Null
        }
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Application stopped."
}

function Find-Python {
    $candidates = @(
        $env:EXPENSE_REPORT_PYTHON,
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        (Join-Path $env:USERPROFILE ".venvs\expense-report-web\Scripts\python.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($candidate in $candidates) {
        & $candidate -c "import sys; assert sys.version_info[:2] == (3, 12)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }

    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3.12 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
            & $launcher.Source -3.12 -m venv (Join-Path $ProjectRoot ".venv")
            return $venvPython
        }
    }

    throw "Python 3.12 was not found. Install Python 3.12 or set EXPENSE_REPORT_PYTHON to python.exe."
}

function Ensure-PythonDependencies([string]$Python) {
    & $Python -c "import alembic, fastapi, paddleocr, sqlalchemy, uvicorn" 2>$null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host "Installing Python components for the first launch..."
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Failed to update pip." }
    & $Python -m pip install -e (Join-Path $ProjectRoot "backend")
    if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies." }
}

function Ensure-FrontendBuild {
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $nodePath = if ($nodeCommand) { $nodeCommand.Source } else { $null }
    if (-not $nodePath) {
        $nodeCandidates = @(
            (Join-Path $env:ProgramFiles "nodejs\node.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe")
        )
        $nodePath = $nodeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $nodePath) {
        throw "Node.js was not found. Install Node.js 22 or newer."
    }

    $frontendDir = Join-Path $ProjectRoot "frontend"
    $needsInstall = -not (Test-Path (Join-Path $frontendDir "node_modules"))
    if ($needsInstall) {
        Write-Host "Installing frontend components for the first launch..."
        Invoke-Pnpm @("install", "--frozen-lockfile", "--dir", $frontendDir)
        if ($LASTEXITCODE -ne 0) { throw "Failed to install frontend dependencies." }
    }

    $buildId = Join-Path $frontendDir ".next\BUILD_ID"
    $needsBuild = -not (Test-Path $buildId)
    if (-not $needsBuild) {
        $buildTime = (Get-Item $buildId).LastWriteTimeUtc
        $inputs = @(
            (Join-Path $frontendDir "package.json"),
            (Join-Path $frontendDir "pnpm-lock.yaml"),
            (Join-Path $frontendDir "next.config.ts")
        )
        $inputs += Get-ChildItem (Join-Path $frontendDir "src") -Recurse -File | Select-Object -ExpandProperty FullName
        $needsBuild = $null -ne ($inputs | Where-Object { (Get-Item $_).LastWriteTimeUtc -gt $buildTime } | Select-Object -First 1)
    }

    if ($needsBuild) {
        Write-Host "Building the current interface..."
        Push-Location $frontendDir
        try {
            Invoke-Pnpm @("build")
            if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
        }
        finally {
            Pop-Location
        }
    }

    $standaloneDir = Join-Path $frontendDir ".next\standalone"
    $standaloneStatic = Join-Path $standaloneDir ".next\static"
    $standalonePublic = Join-Path $standaloneDir "public"
    New-Item -ItemType Directory -Path $standaloneStatic, $standalonePublic -Force | Out-Null
    Copy-Item -Path (Join-Path $frontendDir ".next\static\*") -Destination $standaloneStatic -Recurse -Force
    Copy-Item -Path (Join-Path $frontendDir "public\*") -Destination $standalonePublic -Recurse -Force

    return $nodePath
}

function Invoke-Pnpm([string[]]$PnpmArguments) {
    $pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if ($pnpm) {
        & $pnpm.Source @PnpmArguments | Out-Host
        return
    }

    $corepackCommand = Get-Command corepack.cmd -ErrorAction SilentlyContinue
    $corepackPath = if ($corepackCommand) { $corepackCommand.Source } else { Join-Path $env:ProgramFiles "nodejs\corepack.cmd" }
    if (-not (Test-Path $corepackPath)) {
        throw "The interface needs rebuilding, but pnpm and corepack were not found. Install Node.js 22 or newer."
    }
    & $corepackPath pnpm @PnpmArguments | Out-Host
}

if ($Stop) {
    Stop-AppProcesses
    exit 0
}

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

if ($Restart) {
    Stop-AppProcesses
    Start-Sleep -Seconds 1
}
elseif ((Test-AppPort $BackendPort) -and (Test-AppPort $FrontendPort)) {
    Write-Host "Application is already running: $AppUrl"
    if (-not $NoBrowser) { Start-Process $AppUrl }
    exit 0
}

$python = Find-Python
Ensure-PythonDependencies $python
$node = Ensure-FrontendBuild

Write-Host "Preparing the database..."
Push-Location $ProjectRoot
try {
    & $python -m alembic -c "backend/alembic.ini" upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
}
finally {
    Pop-Location
}

$backendOut = Join-Path $RuntimeDir "backend.out.log"
$backendErr = Join-Path $RuntimeDir "backend.err.log"
$frontendOut = Join-Path $RuntimeDir "frontend.out.log"
$frontendErr = Join-Path $RuntimeDir "frontend.err.log"
foreach ($log in @($backendOut, $backendErr, $frontendOut, $frontendErr)) {
    Set-Content -LiteralPath $log -Value ""
}

$env:PYTHONPATH = $ProjectRoot
$env:ENVIRONMENT = "local-desktop"
$env:LOCAL_AUTH_BYPASS = "true"
$env:LOCAL_AUTH_EMAIL = "aleksandr.drugalev@h-xgroup.com"
$backend = $null
$frontend = $null
try {
    $backend = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
        -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru

    $standaloneDir = Join-Path $ProjectRoot "frontend\.next\standalone"
    $frontendServer = Join-Path $standaloneDir "server.js"
    $env:HOSTNAME = "127.0.0.1"
    $env:PORT = "3000"
    $frontend = Start-Process -FilePath $node `
        -ArgumentList @($frontendServer) `
        -WorkingDirectory $standaloneDir -WindowStyle Hidden `
        -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
}
catch {
    foreach ($startedProcess in @($frontend, $backend)) {
        if ($startedProcess -and -not $startedProcess.HasExited) {
            & taskkill.exe /PID $startedProcess.Id /T /F 2>$null | Out-Null
        }
    }
    throw
}

@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $PidFile -Encoding UTF8

$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
    if ($backend.HasExited -or $frontend.HasExited) {
        Stop-AppProcesses
        throw "One of the application components stopped during startup. Logs: $RuntimeDir"
    }
    if ((Test-AppPort $BackendPort) -and (Test-AppPort $FrontendPort)) {
        Write-Host "Application started: $AppUrl"
        if (-not $NoBrowser) { Start-Process $AppUrl }
        exit 0
    }
    Start-Sleep -Seconds 2
}

Stop-AppProcesses
throw "Application startup timed out. Logs: $RuntimeDir"
