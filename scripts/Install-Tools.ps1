param([switch]$IncludeAntivirus)
$ErrorActionPreference='Stop'
$projectPath=Split-Path $PSScriptRoot -Parent
$toolsPath=Join-Path $projectPath 'tools'
New-Item -ItemType Directory -Force -Path $toolsPath | Out-Null
function Get-File([string]$Url,[string]$Destination) {
    if (-not (Test-Path -LiteralPath $Destination)) { Invoke-WebRequest -Uri $Url -OutFile $Destination }
}
# Arquivos dos distribuidores oficiais; apenas extração local, sem instaladores globais.
Get-File 'https://www.7-zip.org/a/7zr.exe' (Join-Path $toolsPath '7zr.exe')
Get-File 'https://www.7-zip.org/a/7z2409-x64.exe' (Join-Path $toolsPath '7zip-setup.exe')
& (Join-Path $toolsPath '7zr.exe') x (Join-Path $toolsPath '7zip-setup.exe') "-o$(Join-Path $toolsPath '7zip')" -y
if ($LASTEXITCODE -ne 0) { throw 'Falha ao extrair 7-Zip.' }
Get-File 'https://github.com/oschwartz10612/poppler-windows/releases/download/v26.09.0-0/Release-26.09.0-0.zip' (Join-Path $toolsPath 'poppler.zip')
Expand-Archive -LiteralPath (Join-Path $toolsPath 'poppler.zip') -DestinationPath (Join-Path $toolsPath 'poppler') -Force
Get-File 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe' (Join-Path $toolsPath 'tesseract-setup.exe')
& (Join-Path $toolsPath '7zip\7z.exe') x (Join-Path $toolsPath 'tesseract-setup.exe') "-o$(Join-Path $toolsPath 'tesseract')" -y
if ($LASTEXITCODE -ne 0) { throw 'Falha ao extrair Tesseract.' }
Get-File 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/por.traineddata' (Join-Path $toolsPath 'tesseract\tessdata\por.traineddata')
if ($IncludeAntivirus) {
    Get-File 'https://www.clamav.net/downloads/production/clamav-1.4.6.win.x64.zip' (Join-Path $toolsPath 'clamav.zip')
    Expand-Archive -LiteralPath (Join-Path $toolsPath 'clamav.zip') -DestinationPath (Join-Path $toolsPath 'clamav') -Force
}
Write-Output 'Ferramentas extraídas. Instale requirements-ocr.txt e execute Run-Acervo.ps1 -Mode check.'
