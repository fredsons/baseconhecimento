param([string]$PythonPath='')
$ErrorActionPreference='Stop'
$projectPath=Split-Path $PSScriptRoot -Parent
if (-not $PythonPath) {
    $PythonPath=@((Join-Path $projectPath '.venv\Scripts\python.exe'),(Join-Path $projectPath '..\..\work\venv\Scripts\python.exe')) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $PythonPath) { throw 'Informe -PythonPath.' }
$PythonPath=(Resolve-Path -LiteralPath $PythonPath).Path
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $principal.UserId
$options=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
foreach ($mode in @('web','worker')) {
    $name='Acervo-'+$mode
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "A tarefa $name já existe; não foi substituída." }
    $runner=Join-Path $PSScriptRoot 'Run-Acervo.ps1'
    $arguments='-NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -WindowStyle Hidden -File "{0}" -Mode {1} -PythonPath "{2}"' -f $runner,$mode,$PythonPath
    $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $projectPath
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $options -Principal $principal | Select-Object TaskName,State
}
