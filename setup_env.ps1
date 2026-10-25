param(
    [switch]$Recreate,
    [string]$IndexUrl = 'https://pypi.org/simple',
    [switch]$NoProxy
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if ($Recreate -and (Test-Path -LiteralPath $venvPath)) {
    $resolvedVenv = (Resolve-Path -LiteralPath $venvPath).Path
    if ($resolvedVenv -ne (Join-Path $projectRoot '.venv')) {
        throw 'Refusing to delete a virtual environment outside this project.'
    }
    $venvItems = @((Get-Item -LiteralPath $venvPath -Force)) + @(Get-ChildItem -LiteralPath $venvPath -Force -Recurse)
    if (@($venvItems | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
        throw 'Refusing to recursively delete linked paths in the virtual environment.'
    }
    $runningPython = @(Get-Process -Name python,pythonw -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($venvPath + '\', [StringComparison]::OrdinalIgnoreCase)
    })
    if ($runningPython.Count) { throw 'Close the project Python processes before recreating the environment.' }
    Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3.11 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 environment creation failed. Check py -0p.' }
}
& $venvPython -c "import sys; assert sys.version_info[:2] == (3, 11), 'Python 3.11 is required'; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw 'Unexpected Python interpreter. Re-run with -Recreate.' }
$previousNoProxy = [Environment]::GetEnvironmentVariable('NO_PROXY', 'Process')
try {
    if ($NoProxy) { $env:NO_PROXY = '*' }
    $pipArguments = @('-m', 'pip', 'install', '--disable-pip-version-check', '--timeout', '30', '--retries', '1', '--index-url', $IndexUrl)
    $localWheelCache = Join-Path $projectRoot '.bootstrap'
    if (Test-Path -LiteralPath $localWheelCache) { $pipArguments += @('--find-links', $localWheelCache) }
    $pipArguments += @('-r', (Join-Path $projectRoot 'requirements.txt'))
    & $venvPython @pipArguments
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Fix the connection and re-run setup_env.ps1.' }
} finally {
    if ($null -eq $previousNoProxy) {
        Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue
    } else {
        $env:NO_PROXY = $previousNoProxy
    }
}
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) {
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination (Join-Path $projectRoot '.env')
}
Write-Host 'Environment ready. Fill DEEPSEEK_API_KEY in .env, then run start_pet.cmd.'
