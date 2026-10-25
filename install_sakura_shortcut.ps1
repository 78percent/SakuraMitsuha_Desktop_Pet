[CmdletBinding()]
param([string]$DesktopPath, [string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = $PSScriptRoot }
$shellObject = New-Object -ComObject WScript.Shell
if ([string]::IsNullOrWhiteSpace($DesktopPath)) { $DesktopPath = [Environment]::GetFolderPath('DesktopDirectory') }
if ([string]::IsNullOrWhiteSpace($DesktopPath)) { $DesktopPath = $shellObject.SpecialFolders.Item('Desktop') }
if ([string]::IsNullOrWhiteSpace($DesktopPath)) { throw 'Cannot resolve Desktop. Supply -DesktopPath with the real desktop directory.' }
$resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).Path
$resolvedDesktop = (Resolve-Path -LiteralPath $DesktopPath).Path
$interpreterPath = Join-Path $resolvedProject '.venv\Scripts\pythonw.exe'
$entryPath = Join-Path $resolvedProject 'run_pet.py'
$iconPath = Join-Path $resolvedProject 'CetaPet\asset_library\sakura\sakura.ico'
foreach ($requiredPath in @($interpreterPath,$entryPath,$iconPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) { throw "Startup file missing: $requiredPath. See README and rerun setup_env.ps1 or rebuild the icon." }
}
$linkPath = Join-Path $resolvedDesktop '佐仓三叶.lnk'
$backupPath = $null
if (Test-Path -LiteralPath $linkPath) {
    $oldLink = $shellObject.CreateShortcut($linkPath)
    if ($oldLink.TargetPath -ne $interpreterPath -or $oldLink.WorkingDirectory -ne $resolvedProject) {
        $backupDir = Join-Path $resolvedProject '.bootstrap\shortcut-backups'
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $backupPath = Join-Path $backupDir ('佐仓三叶-before-' + [Guid]::NewGuid().ToString('N') + '.lnk')
        Copy-Item -LiteralPath $linkPath -Destination $backupPath
        Write-Warning "Existing unrelated shortcut preserved at $backupPath"
    }
}
$link = $shellObject.CreateShortcut($linkPath)
$link.TargetPath = $interpreterPath
$link.Arguments = '"' + $entryPath + '"'
$link.WorkingDirectory = $resolvedProject
$link.IconLocation = $iconPath + ',0'
$link.Description = '佐仓三叶桌宠：再次打开可召回已运行的角色。'
$link.WindowStyle = 1
$link.Save()
[pscustomobject]@{shortcut=$linkPath;target=$link.TargetPath;arguments=$link.Arguments;workingDirectory=$link.WorkingDirectory;icon=$link.IconLocation;backup=$backupPath} | ConvertTo-Json -Compress
