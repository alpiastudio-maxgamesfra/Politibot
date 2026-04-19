# === CONFIGURATION ===
$projectPath = "C:\Python\Projects\Politibot"
$archivePath = "$projectPath\Archives"

# Crée le dossier Archives s'il n'existe pas
if (!(Test-Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath | Out-Null
}

# === VERSIONING ===
# Version basée sur la date : ex : 2025-02
$version = (Get-Date -Format "yyyy-MM")

# Nom du fichier ZIP
$zipName = "Politibot-$version.zip"
$zipFullPath = "$archivePath\$zipName"

# === FONCTION : suppression robuste ===
function Remove-LockedFile {
    param([string]$Path)

    if (Test-Path $Path) {
        try {
            Remove-Item $Path -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Le fichier $Path est verrouillé. Tentative de libération..."
            Start-Sleep -Seconds 1

            try {
                Remove-Item $Path -Force -ErrorAction Stop
            }
            catch {
                Write-Host "Impossible de supprimer $Path, création d'un nom alternatif."
                return $false
            }
        }
    }
    return $true
}

# === GESTION DU FICHIER ZIP EXISTANT ===
$zipPath = $zipFullPath

if (-not (Remove-LockedFile $zipPath)) {
    $zipPath = "$archivePath\Politibot-$version-alt.zip"
}

# === ARCHIVAGE (.NET, fiable) ===
Write-Host "Archivage de la version $version..."

# Charge la classe .NET pour la compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

# Supprime l’archive si elle existe déjà (sécurité)
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# Crée l’archive ZIP avec .NET (plus fiable que Compress-Archive)
[System.IO.Compression.ZipFile]::CreateFromDirectory($projectPath, $zipPath)

Write-Host "Archive creee : $zipPath"

# === FIN ===
Write-Host "Archivage termine. Vous pouvez maintenant mettre a jour Politibot."