param(
    [ValidateSet('web','worker','backup','check')][string]$Mode='web',
    [string]$PythonPath='',
    [string]$BackupDirectory='',
    [int]$Port=8000
)
$ErrorActionPreference='Stop'
$projectPath=Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $projectPath
try {
if (-not $PythonPath) {
    $candidates=@((Join-Path $projectPath '.venv\Scripts\python.exe'),(Join-Path $projectPath '..\..\work\venv\Scripts\python.exe'))
    $PythonPath=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $PythonPath) { throw 'Python não localizado. Crie .venv ou informe -PythonPath com o caminho do python.exe instalado.' }
$PythonPath=(Resolve-Path -LiteralPath $PythonPath).Path
$envFile=Join-Path $projectPath '.env'
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*([A-Z_][A-Z0-9_]*)\s*=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1],$Matches[2].Trim().Trim('"').Trim("'"),'Process')
        }
    }
}
if (-not $env:DEBUG) { $env:DEBUG='1' }
if (-not $env:DATA_DIR) { $env:DATA_DIR=Join-Path $projectPath 'var' }
switch ($Mode) {
    'web' {
        & $PythonPath manage.py prepare_assets
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o visualizador local.' }
        & $PythonPath manage.py migrate --noinput
        if ($LASTEXITCODE -ne 0) { throw 'Falha nas migrações.' }
        & $PythonPath manage.py collectstatic --noinput
        if ($LASTEXITCODE -ne 0) { throw 'Falha nos arquivos públicos.' }
        & $PythonPath manage.py serve_windows --port $Port
    }
    'worker' { & $PythonPath manage.py qcluster }
    'check' { & $PythonPath manage.py doctor --strict }
    'backup' {
        if (-not $BackupDirectory) { $BackupDirectory=Join-Path $projectPath '..\backups-acervo' }
        $result=& $PythonPath manage.py backup $BackupDirectory
        if ($LASTEXITCODE -ne 0) { throw 'Falha no backup.' }
        $backupPath=($result | Select-Object -Last 1).Trim()
        & $PythonPath manage.py verify_backup $backupPath
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao verificar o backup.' }
        Write-Output $backupPath
    }
}
if ($LASTEXITCODE -ne 0) { throw "O comando terminou com erro: $LASTEXITCODE" }
} finally { Pop-Location }
