param([string]$PythonPath='', [string]$BackupDirectory='', [string]$TaskName='Acervo-Backup')
$ErrorActionPreference='Stop'
$projectPath=Split-Path $PSScriptRoot -Parent
if (-not $PythonPath) {
    $PythonPath=@((Join-Path $projectPath '.venv\Scripts\python.exe'),(Join-Path $projectPath '..\..\work\venv\Scripts\python.exe')) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $PythonPath) { throw 'Informe -PythonPath.' }
$PythonPath=(Resolve-Path -LiteralPath $PythonPath).Path
if (-not $BackupDirectory) { $BackupDirectory=Join-Path $projectPath '..\backups-acervo' }
$BackupDirectory=[IO.Path]::GetFullPath($BackupDirectory)
New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
try { $existing=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue }
catch { throw 'Este terminal não conseguiu acessar o Agendador de Tarefas do Windows. Execute este script no seu PowerShell fora do aplicativo.' }
if ($existing) { throw "A tarefa $TaskName já existe; não foi substituída." }
$runner=Join-Path $PSScriptRoot 'Run-Acervo.ps1'
$arguments='-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}" -Mode backup -PythonPath "{1}" -BackupDirectory "{2}"' -f $runner,$PythonPath,$BackupDirectory
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $projectPath
$trigger=New-ScheduledTaskTrigger -Daily -At '02:00'
$options=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $options -Principal $principal -Description 'Backup SQLite consistente, PDFs privados e verificação de integridade do Acervo.' | Select-Object TaskName,State
