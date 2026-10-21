$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Prospect Engine - Installation locale (aucune API payante, aucun Docker)'
try {
    $python = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys; assert sys.version_info >= (3,12)"
        if ($LASTEXITCODE -eq 0) { $python = 'py' }
    }
    if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
        & python -c "import sys; assert (3,12) <= sys.version_info < (3,14)"
        if ($LASTEXITCODE -eq 0) { $python = 'python' }
    }
    if (-not $python) {
        Write-Host 'Python 3.12 est requis. Installez-le depuis https://www.python.org/downloads/windows/ (cocher Add Python to PATH).'
        Write-Host 'Ou, si winget est disponible : winget install --id Python.Python.3.12 -e'
        throw 'Relancez Installer.ps1 après installation de Python. Node.js et Playwright ne sont pas requis.'
    }
    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        if ($python -eq 'py') { & py -3.12 -m venv .venv } else { & python -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Création de l’environnement Python impossible.' }
    }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances impossible. Vérifiez Internet et le journal ci-dessus.' }
    & .\.venv\Scripts\python.exe -m app.manage migrate
    if ($LASTEXITCODE -ne 0) { throw 'Initialisation de la base impossible.' }
    & .\.venv\Scripts\python.exe scripts\launcher.py start --no-browser
    if ($LASTEXITCODE -ne 0) { throw 'Test de démarrage non validé.' }
    & .\.venv\Scripts\python.exe scripts\launcher.py stop
    if ($LASTEXITCODE -ne 0) { throw 'Arrêt des services non confirmé.' }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Prospect Engine.lnk'))
    $shortcut.TargetPath = Join-Path $PSScriptRoot 'Start.bat'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Save()
    Write-Host 'Installation terminée. Double-cliquez sur Start.bat ou le raccourci du Bureau.'
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }
