param([switch]$SetupOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $probe = 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
    $usable = $false
    if (Test-Path -LiteralPath $venvPython) {
        & $venvPython -c $probe 2>$null
        $usable = $LASTEXITCODE -eq 0
        if (-not $usable) { throw 'The existing .venv is invalid or older than Python 3.10. Rename .venv and run setup again.' }
    }
    if (-not $usable) {
        # Probe execution: a launcher can exist without a matching runtime.
        $candidates = @(
            @{Command='python'; Arguments=@()},
            @{Command='py'; Arguments=@()},
            @{Command='py'; Arguments=@('-3')},
            @{Command='python3'; Arguments=@()}
        )
        $selected = $null
        foreach ($candidate in $candidates) {
            $exe = Get-Command $candidate.Command -ErrorAction SilentlyContinue
            if (-not $exe) { continue }
            $previous = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $probeArgs = @($candidate.Arguments) + @('-c', $probe)
            & $exe.Source @probeArgs 2>$null
            $code = $LASTEXITCODE
            $ErrorActionPreference = $previous
            if ($code -eq 0) { $selected = $candidate; break }
        }
        if (-not $selected) { throw 'No working Python 3.10+ found. Install from https://www.python.org/downloads/windows/ with Add Python to PATH, reopen the terminal, then retry. Diagnostic commands: python --version and py --list.' }
        Write-Host '[MD TECH] Creating Python environment...'
        $createArgs = @($selected.Arguments) + @('-m', 'venv', '.venv')
        & $selected.Command @createArgs
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed. Check Python includes venv and this folder is writable.' }
    }
    Write-Host '[MD TECH] Installing dependencies...'
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Check internet access and the pip error above.' }
    if ($SetupOnly) { Write-Host '[MD TECH] Setup complete.'; exit 0 }
    Write-Host '[MD TECH] Open http://127.0.0.1:8765'
    & $venvPython (Join-Path $PSScriptRoot 'run.py')
    exit $LASTEXITCODE
} catch {
    Write-Host "[MD TECH] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
