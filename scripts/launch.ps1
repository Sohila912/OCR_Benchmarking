param(
    [switch]$CheckOnly,
    [switch]$SmokeCheck
)

$ErrorActionPreference = 'Stop'
# Some Windows environments expose both PATH and Path. PowerShell preserves
# both names in the inherited environment block, and Start-Process rejects the
# duplicate keys. Keep one canonical Path entry for all child processes.
$normalizedPath = $env:Path
$env:PATH = $null
$env:Path = $normalizedPath
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$backend = $null
$frontend = $null
$apiOutMonitor = $null
$apiErrMonitor = $null

function Find-Python {
    # Prefer working project environments, then an explicit override/discovered installations.
    $candidates = @()
    if ($env:OCR_PYTHON) { $candidates += $env:OCR_PYTHON }
    $candidates += @('.venv-ocr\Scripts\python.exe', '.venv\Scripts\python.exe', 'OCR\.venv\Scripts\python.exe') |
        ForEach-Object { Join-Path $repoRoot $_ }
    $candidates += @(Get-Command python.exe -All -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $registered = & $pyLauncher.Source -0p 2>$null
        foreach ($line in $registered) {
            if ($line -match '([A-Za-z]:\\.*python\.exe)\s*$') { $candidates += $matches[1] }
        }
    }
    if ($env:LOCALAPPDATA) {
        $installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
        $candidates += @(Get-ChildItem -LiteralPath $installRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'python.exe' })
    }
    # Also discover portable Python installations beside the repository.
    $candidates += @(Get-ChildItem -LiteralPath (Split-Path -Parent $repoRoot) -Directory -Filter '*python*' |
        ForEach-Object { Join-Path $_.FullName 'python.exe' })
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (!(Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        if ($candidate -like '*\WindowsApps\*') { continue }
        # Windows PowerShell turns native stderr into terminating errors under Stop.
        # A stale venv must be skipped so discovery can try the next interpreter.
        $savedPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $probe = & $candidate -B -c 'import sys; assert sys.version_info >= (3, 10); print(sys.executable)' 2>$null
            $probeExitCode = $LASTEXITCODE
        } finally { $ErrorActionPreference = $savedPreference }
        if ($probeExitCode -eq 0 -and $probe) { return [string]($probe | Select-Object -Last 1) }
    }
    throw 'No working Python 3.10+ found. Install Python, or set OCR_PYTHON to its python.exe path.'
}

function Wait-Ready([string]$Url, $Process, [string]$Label) {
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        $Process.Refresh()
        if ($Process.HasExited) { throw "$Label exited. See the log files printed below." }
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    throw "$Label did not become ready within 60 seconds. See the log files."
}

function Assert-FreePort([string]$HostName, [int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $client.ConnectAsync($HostName, $Port)
        if ($connection.Wait(500) -and $client.Connected) {
            throw "Port $Port is already in use. Close the previous OCR launcher or the application using this port, then try again."
        }
    } catch [System.AggregateException] {
        # A refused connection means no process is listening.
    } finally { $client.Dispose() }
}

function Ensure-Ollama([string]$OllamaHost, [string]$Model) {
    # Avoid Windows localhost/IPv6 proxy resolution quirks when talking to the
    # local Ollama daemon from PowerShell.
    $requestHost = $OllamaHost -replace '://localhost(?=[:/]|$)', '://127.0.0.1'
    $tagsUrl = ($requestHost.TrimEnd('/')) + '/api/tags'
    $tags = $null
    try { $tags = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 2 } catch { }
    if (!$tags) {
        $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
        if (!$ollamaCommand) {
            $runningOllama = Get-Process -Name ollama -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($runningOllama -and $runningOllama.Path) {
                $ollamaCommand = [pscustomobject]@{ Source = $runningOllama.Path }
            }
        }
        if (!$ollamaCommand) {
            $knownOllamaPaths = @(
                (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
                (Join-Path $env:ProgramFiles 'Ollama\ollama.exe')
            )
            foreach ($candidate in $knownOllamaPaths) {
                $exists = $false
                try { $exists = $candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf -ErrorAction SilentlyContinue) } catch { }
                if ($exists) {
                    $ollamaCommand = [pscustomobject]@{ Source = $candidate }
                    break
                }
            }
        }
        if ($ollamaCommand) {
            Write-Host "Ollama API is unavailable; starting Ollama at $OllamaHost..."
            try { Start-Process -FilePath $ollamaCommand.Source -ArgumentList 'serve' -WindowStyle Hidden -ErrorAction Stop | Out-Null }
            catch {
                throw "Could not start Ollama: $($_.Exception.Message)"
            }
            $deadline = (Get-Date).AddSeconds(30)
            while ((Get-Date) -lt $deadline -and !$tags) {
                Start-Sleep -Milliseconds 500
                try { $tags = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 2 } catch { }
            }
        } else {
            throw 'Ollama API is unavailable and ollama.exe was not found. Install Ollama or start its server before running the application.'
        }
    }
    if (!$tags) {
        throw 'Ollama did not become ready within 30 seconds. Start Ollama and run the application again.'
    }

    $installed = @($tags.models | ForEach-Object { [string]$_.name })
    if ($installed -contains $Model) {
        Write-Host "Ollama model ready: $Model" -ForegroundColor Green
        return
    }

    Write-Host "Ollama model $Model is missing; downloading through /api/pull..."
    Add-Type -AssemblyName System.Net.Http
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromHours(6)
    try {
        $body = ConvertTo-Json @{ name = $Model; stream = $true } -Compress
        $content = New-Object -TypeName System.Net.Http.StringContent -ArgumentList @($body, [Text.Encoding]::UTF8, 'application/json')
        $request = New-Object -TypeName System.Net.Http.HttpRequestMessage -ArgumentList @([System.Net.Http.HttpMethod]::Post, (($requestHost.TrimEnd('/')) + '/api/pull'))
        $request.Content = $content
        # Read the newline-delimited pull stream as it arrives so the launcher
        # prints download progress instead of appearing frozen for an hour.
        $response = $client.SendAsync($request, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        if (!$response.IsSuccessStatusCode) {
            throw "Ollama /api/pull failed with HTTP $([int]$response.StatusCode): $Model"
        }
        $reader = New-Object -TypeName System.IO.StreamReader -ArgumentList @($response.Content.ReadAsStreamAsync().GetAwaiter().GetResult())
        $pullError = $null
        $lastPullStatus = $null
        $lastPullPercent = -1
        while (($line = $reader.ReadLine()) -ne $null) {
            if (!$line.Trim()) { continue }
            try {
                $event = $line | ConvertFrom-Json
                if ($event.error) { $pullError = [string]$event.error; Write-Host "Ollama pull error: $pullError" -ForegroundColor Yellow; break }
                if ($event.status) {
                    $percent = if ($event.completed -and $event.total) { [math]::Round(100 * $event.completed / $event.total, 1) } else { -1 }
                    if ($event.status -ne $lastPullStatus -or ($percent -ge 0 -and $percent -ne $lastPullPercent)) {
                        $progress = if ($percent -ge 0) { " ($percent%)" } else { '' }
                        Write-Host "Ollama pull: $($event.status)$progress"
                        $lastPullStatus = [string]$event.status
                        $lastPullPercent = $percent
                    }
                }
            } catch { Write-Host "Ollama pull: $line" }
        }
        $reader.Dispose()
        $request.Dispose()
        if ($pullError) {
            throw "Ollama model download was incomplete: $pullError"
        }
    } catch {
        throw "Ollama model download failed or was interrupted: $($_.Exception.Message)"
    } finally {
        $client.Dispose()
    }

    # A successful stream is not enough: verify Ollama registered the exact tag.
    try { $tags = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 5 } catch {
        throw 'Ollama pull finished, but /api/tags could not be queried; model availability is unconfirmed.'
    }
    $installed = @($tags.models | ForEach-Object { [string]$_.name })
    if ($installed -contains $Model) {
        Write-Host "Ollama model ready: $Model" -ForegroundColor Green
    } else {
        throw "Ollama pull completed, but exact model tag '$Model' is still missing. The download may be incomplete or registered under a different tag."
    }
}

try {
    Write-Host "`nOCR Benchmarking / OCR Service" -ForegroundColor Cyan
    $python = Find-Python
    Write-Host "Python: $python"
    $dependencyProbe = @'
import importlib.util, json
modules = ['fastapi', 'uvicorn', 'pydantic', 'python_multipart', 'dotenv', 'pdf2image', 'PIL', 'requests', 'streamlit']
print(json.dumps([name for name in modules if importlib.util.find_spec(name) is None]))
'@
    # Explicitly enumerate JSON arrays on Windows PowerShell 5.1, including [].
    $missing = @((& $python -B -c $dependencyProbe) | ConvertFrom-Json | ForEach-Object { $_ })
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Python dependencies.' }
    if ($missing.Count -gt 0) {
        Write-Host "Missing packages: $($missing -join ', ')" -ForegroundColor Yellow
        if ($CheckOnly -or $SmokeCheck) { throw 'Install requirements.txt in the selected Python environment before verification.' }
        Write-Host "First-time setup can install the core requirements into: $python"
        Write-Host 'Paddle/Docling packages and model files are installed separately.'
        $answer = Read-Host 'Install these dependencies now? Type Y to approve'
        if ($answer -notmatch '^(y|yes)$') { throw 'Dependency installation was not approved. Nothing was installed.' }
        & $python -m pip install -r (Join-Path $repoRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Review the pip output above.' }
    }

    $envFile = Join-Path $repoRoot '.env'
    if (!(Test-Path -LiteralPath $envFile)) {
        Copy-Item -LiteralPath (Join-Path $repoRoot '.env.example') -Destination $envFile
        Write-Host 'Created .env from the portable example.'
    }
    $settingsProbe = @'
import json
from OCR.config import load_settings
s = load_settings()
print(json.dumps({'host': s.api_host, 'port': s.api_port, 'provider': s.provider, 'tesseract': s.tesseract_cmd,
                  'poppler': str(s.poppler_path) if s.poppler_path else None, 'languages': s.tesseract_lang,
                  'ollama_host': s.ollama_host, 'ollama_model': s.ollama_ocr_model}))
'@
    $config = (& $python -B -c $settingsProbe) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Invalid application configuration. Check .env and the error above.' }

    # Resolve the default Tesseract command through Windows installation discovery.
    # Explicit paths/commands from .env are respected; no machine-specific path is in source.
    if ($config.tesseract -eq 'tesseract' -and !(Get-Command tesseract.exe -ErrorAction SilentlyContinue)) {
        foreach ($programRoot in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
            if (!$programRoot) { continue }
            $binary = Join-Path $programRoot 'Tesseract-OCR\tesseract.exe'
            if (Test-Path -LiteralPath $binary) {
                $env:OCR_TESSERACT_CMD = $binary
                Write-Host "Detected Tesseract: $binary"
                break
            }
        }
    }
    if (!$config.poppler) {
        $pdfInfo = Get-Command pdfinfo.exe -ErrorAction SilentlyContinue
        if ($pdfInfo) {
            $popplerDirectory = Split-Path -Parent $pdfInfo.Source
            if (Test-Path -LiteralPath (Join-Path $popplerDirectory 'pdftoppm.exe')) {
                $env:OCR_POPPLER_PATH = $popplerDirectory
                Write-Host "Detected Poppler: $popplerDirectory"
            }
        }
    }
    if ($config.provider -eq 'tesseract') {
        $toolProbe = @'
from OCR.config import load_settings
from OCR.pdf import require_pdf_renderer
from OCR.providers.tesseract import probe_tesseract
s = load_settings()
require_pdf_renderer(s.poppler_path)
print(probe_tesseract(s.tesseract_cmd, s.tesseract_lang, 10))
print('Configured language packs: ' + s.tesseract_lang)
'@
        & $python -B -c $toolProbe
        if ($LASTEXITCODE -ne 0) { throw 'Tesseract/Poppler preflight failed. Check the paths and language packs in .env.' }
    } else {
        Write-Host "Selected provider: $($config.provider). Its local model assets are checked on first extraction."
    }

    if (!$CheckOnly -and !$SmokeCheck) {
        $modelProbe = @'
import importlib.metadata
import json
import re
from OCR.config import REPOSITORY_ROOT, load_settings

requirements = {}
for raw in (REPOSITORY_ROOT / 'requirements-models.txt').read_text(encoding='utf-8-sig').splitlines():
    line = raw.split('#', 1)[0].strip()
    if not line:
        continue
    # Use single quotes here because PowerShell strips embedded double quotes
    # when passing a here-string to python's -c argument.
    match = re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^;\s]+)', line)
    if not match:
        # Ranged optional dependencies (for example ollama>=...,<1) are
        # installed normally but are not version-pinned for this probe.
        continue
    requirements[match.group(1).lower().replace('_', '-')] = match.group(2)

settings = load_settings()
paths = {
    'paddle_vl': settings.paddle_vl_model_dir or REPOSITORY_ROOT / 'models' / 'PaddleOCR-VL-1.6',
    'paddle_layout': settings.paddle_layout_model_dir or REPOSITORY_ROOT / 'models' / 'PP-DocLayoutV3',
    'docling': settings.docling_artifacts_path or REPOSITORY_ROOT / 'models' / 'docling',
}
versions = {}
for package, required in requirements.items():
    try:
        installed = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        installed = None
    versions[package] = {'required': required, 'installed': installed, 'ready': installed == required}

def has_files(path, required_files=()):
    return path.is_dir() and all((path / name).is_file() for name in required_files) and any(
        item.is_file() for item in path.rglob('*'))

assets = {
    'paddle_vl': has_files(paths['paddle_vl'], ('inference.yml',)),
    'paddle_layout': has_files(paths['paddle_layout'], ('inference.json', 'inference.pdiparams', 'inference.yml')),
    'docling': has_files(paths['docling']),
}
print(json.dumps({
    'versions': versions,
    'assets': assets,
    'paths': {name: str(path) for name, path in paths.items()},
    'ready': all(item['ready'] for item in versions.values()) and all(assets.values()),
}))
'@
        $modelStatus = (& $python -B -c $modelProbe) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the Paddle/Docling package versions and model files.' }
        if (!$modelStatus.ready) {
            Write-Host 'Paddle VL and Docling require pinned packages from requirements-models.txt and local model files.'
            Write-Host 'This setup installs those packages, then downloads both providers'' model assets.'
            foreach ($package in $modelStatus.versions.PSObject.Properties) {
                if (!$package.Value.ready) {
                    Write-Host "$($package.Name): installed $($package.Value.installed); required $($package.Value.required)"
                }
            }
            foreach ($asset in $modelStatus.assets.PSObject.Properties) {
                if (!$asset.Value) { Write-Host "$($asset.Name) model files are missing or incomplete." }
            }
            $answer = Read-Host 'Install/provision Paddle VL and Docling now? Type Y to approve'
            if ($answer -match '^(y|yes)$') {
                & $python -m pip install -r (Join-Path $repoRoot 'requirements-models.txt')
                if ($LASTEXITCODE -ne 0) { throw 'Installing requirements-models.txt failed. Review the pip output above.' }
                & $python (Join-Path $repoRoot 'scripts\provision_models.py')
                if ($LASTEXITCODE -ne 0) { throw 'Paddle/Docling model provisioning failed. Review the download output above.' }
                $modelStatus = (& $python -B -c $modelProbe) | ConvertFrom-Json
                if ($LASTEXITCODE -ne 0 -or !$modelStatus.ready) {
                    throw 'Paddle/Docling setup did not pass its package-version and model-file checks.'
                }
            } else {
                Write-Host 'Paddle/Docling setup skipped; the launcher will continue without provisioning those providers.' -ForegroundColor Yellow
            }
        }
        $env:OCR_PADDLE_VL_MODEL_DIR = $modelStatus.paths.paddle_vl
        $env:OCR_PADDLE_LAYOUT_MODEL_DIR = $modelStatus.paths.paddle_layout
        $env:OCR_DOCLING_ARTIFACTS_PATH = $modelStatus.paths.docling
    }

    if ($CheckOnly) { Write-Host 'Launcher preflight passed.' -ForegroundColor Green; exit 0 }

    # A normal launch requires Ollama and the configured model. The model is
    # pulled only when /api/tags confirms that its exact tag is absent.
    if (!$SmokeCheck) { Ensure-Ollama $config.ollama_host $config.ollama_model }

    $localHost = $config.host
    if ($localHost -eq '0.0.0.0') { $localHost = '127.0.0.1' }
    if ($localHost -eq '::') { $localHost = '::1' }
    $urlHost = if ($localHost.Contains(':')) { "[$localHost]" } else { $localHost }
    $apiUrl = "http://${urlHost}:$($config.port)"
    # This launcher starts a local backend; point its child UI to that exact backend.
    $env:OCR_API_URL = $apiUrl
    $uiPort = 8501
    Assert-FreePort $localHost $config.port
    Assert-FreePort '127.0.0.1' $uiPort
    $logDir = Join-Path $repoRoot 'runtime\logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $runId = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $apiOut = Join-Path $logDir "$runId-api.out.log"
    $apiErr = Join-Path $logDir "$runId-api.err.log"
    $uiOut = Join-Path $logDir "$runId-ui.out.log"
    $uiErr = Join-Path $logDir "$runId-ui.err.log"
    New-Item -ItemType File -Path $apiOut, $apiErr, $uiOut, $uiErr -Force | Out-Null
    Write-Host "Logs: $logDir"
    Write-Host 'Starting API...'
    $backend = Start-Process -FilePath $python -ArgumentList '-B -m OCR' -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
    # Stream the API's model lifecycle messages into this launcher terminal while
    # retaining complete stdout/stderr log files under runtime/logs.
    $apiOutMonitor = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-Command', "Get-Content -LiteralPath '$apiOut' -Tail 0 -Wait") -WorkingDirectory $repoRoot -NoNewWindow -PassThru
    $apiErrMonitor = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-Command', "Get-Content -LiteralPath '$apiErr' -Tail 0 -Wait") -WorkingDirectory $repoRoot -NoNewWindow -PassThru
    Wait-Ready "$apiUrl/health" $backend 'API'
    Write-Host 'Starting Streamlit...'
    $frontend = Start-Process -FilePath $python -ArgumentList '-B -m streamlit run OCR/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false' -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $uiOut -RedirectStandardError $uiErr
    Wait-Ready 'http://127.0.0.1:8501/_stcore/health' $frontend 'Streamlit'
    Write-Host "`nReady: http://127.0.0.1:8501" -ForegroundColor Green
    Write-Host "API docs: $apiUrl/docs"
    if ($SmokeCheck) { Write-Host 'Both services passed startup verification; stopping verification processes.'; exit 0 }
    try { Start-Process 'http://127.0.0.1:8501' -ErrorAction Stop }
    catch { Write-Host 'Could not open the browser automatically. Open http://127.0.0.1:8501 manually.' -ForegroundColor Yellow }
    Write-Host 'Keep this launcher open while using OCR.'
    Read-Host 'Press Enter here to stop both services' | Out-Null
} catch {
    Write-Host "`n$($_.Exception.Message)" -ForegroundColor Red
    if ($apiErr -and (Test-Path -LiteralPath $apiErr)) { Get-Content -LiteralPath $apiErr -Tail 12 }
    if ($uiErr -and (Test-Path -LiteralPath $uiErr)) { Get-Content -LiteralPath $uiErr -Tail 12 }
    exit 1
} finally {
    foreach ($ownedProcess in @($apiOutMonitor, $apiErrMonitor, $frontend, $backend)) {
        if ($null -ne $ownedProcess) {
            $ownedProcess.Refresh()
            if (!$ownedProcess.HasExited) { Stop-Process -InputObject $ownedProcess -ErrorAction SilentlyContinue }
        }
    }
}
