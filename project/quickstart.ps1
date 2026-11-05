[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$SkipInstall,
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-CheckedCommand {
    param(
        [string]$Label,
        [string]$Executable,
        [string[]]$Arguments
    )
    Write-Host $Label -ForegroundColor Cyan
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed (exit code $LASTEXITCODE)."
    }
}

$quickstartExit = 0
Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($requiredFile in @('requirements.txt', 'pyproject.toml', 'src/ca/uvic/ecs/csc501/dal/config.properties')) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Missing project file: $requiredFile. Obtain the complete project release."
        }
    }

    $venvPython = Join-Path $PSScriptRoot 'venv/Scripts/python.exe'
    $versionCheck = 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 12) else 1)'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        if ($CheckOnly -or $SkipInstall) {
            throw 'The virtual environment is missing. Run quickstart.ps1 without -CheckOnly or -SkipInstall first.'
        }
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -ne $launcher) {
            Invoke-CheckedCommand -Label 'Checking Python 3.12+' -Executable $launcher.Source -Arguments @('-3', '-c', $versionCheck)
            Invoke-CheckedCommand -Label 'Creating the virtual environment' -Executable $launcher.Source -Arguments @('-3', '-m', 'venv', 'venv')
        }
        else {
            $launcher = Get-Command python -ErrorAction SilentlyContinue
            if ($null -eq $launcher) {
                throw 'Install Python 3.12 or later and add it to PATH, then reopen PowerShell.'
            }
            Invoke-CheckedCommand -Label 'Checking Python 3.12+' -Executable $launcher.Source -Arguments @('-c', $versionCheck)
            Invoke-CheckedCommand -Label 'Creating the virtual environment' -Executable $launcher.Source -Arguments @('-m', 'venv', 'venv')
        }
    }

    Invoke-CheckedCommand -Label 'Checking the project Python version' -Executable $venvPython -Arguments @('-c', $versionCheck)
    if (-not $CheckOnly -and -not $SkipInstall) {
        Invoke-CheckedCommand -Label 'Installing runtime dependencies' -Executable $venvPython -Arguments @('-m', 'pip', 'install', '-r', 'requirements.txt')
        Invoke-CheckedCommand -Label 'Installing PluggedIn' -Executable $venvPython -Arguments @('-m', 'pip', 'install', '-e', '.')
    }

    # The DAL validator reads the selected DB and metadata. Never init or seed.
    Invoke-CheckedCommand -Label 'Validating the selected database' -Executable $venvPython -Arguments @('-m', 'ca.uvic.ecs.csc501.dal.scripts.validate_db')
    if ($CheckOnly) {
        Write-Host 'Quickstart checks passed. No server was started.' -ForegroundColor Green
    }
    else {
        Write-Host "Open http://127.0.0.1:$Port/ in your browser. Press Ctrl+C to stop." -ForegroundColor Green
        Invoke-CheckedCommand -Label 'Starting PluggedIn' -Executable $venvPython -Arguments @('-m', 'uvicorn', 'ca.uvic.ecs.csc501.main:app', '--host', '127.0.0.1', '--port', "$Port")
    }
}
catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    $quickstartExit = 1
}
finally {
    Pop-Location
}
exit $quickstartExit
