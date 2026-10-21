param([ValidateSet('backup','restore','uninstall')][string]$Action)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
try {
    switch ($Action) {
        backup { & $python -m app.manage backup; if ($LASTEXITCODE -ne 0) { throw 'Sauvegarde échouée.' } }
        restore {
            $answer = Read-Host 'Restaurer remplace les données actuelles (une sauvegarde préalable est conservée). Tapez RESTAURER pour confirmer'
            if ($answer -cne 'RESTAURER') { Write-Host 'Annulé.'; exit 0 }
            $file = Read-Host 'Chemin complet du fichier .sqlite à restaurer'
            & $python scripts\launcher.py stop
            if ($LASTEXITCODE -ne 0) { throw 'Arrêt non confirmé.' }
            & $python -m app.manage restore $file --confirm
            if ($LASTEXITCODE -ne 0) { throw 'Restauration échouée. Données préalables conservées en sauvegarde.' }
        }
        uninstall {
            $answer = Read-Host 'Désinstaller les dépendances et le raccourci ? Les données et sources seront conservées. Tapez DESINSTALLER'
            if ($answer -cne 'DESINSTALLER') { Write-Host 'Annulé.'; exit 0 }
            & $python scripts\launcher.py stop
            if ($LASTEXITCODE -ne 0) { throw 'Arrêt non confirmé.' }
            Remove-Item -Recurse -Force '.venv'
            $shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Prospect Engine.lnk'
            if (Test-Path $shortcut) { Remove-Item $shortcut }
            Write-Host 'Dépendances supprimées. Les sources et le dossier data sont conservés. Aucune donnée supprimée.'
        }
    }
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }
