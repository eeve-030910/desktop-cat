param(
    [ValidateSet("Development", "Release")]
    [string]$Channel = "Development"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if ($env:OS -ne "Windows_NT") { throw "Run on Windows." }
if (!(Test-Path ".build-venv\Scripts\python.exe")) {
    py -3 -m venv .build-venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3 / Python launcher is required." }
}
$python = Join-Path $PSScriptRoot ".build-venv\Scripts\python.exe"
& $python -m pip install -r requirements.txt "pyinstaller>=6,<7"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$version = "0.4.5"
$exeName = if ($Channel -eq "Development") { "DesktopCat-Dev-v$version" } else { "DesktopCat-v$version" }
$staging = Join-Path $PSScriptRoot ".build-staging\$Channel"
New-Item -ItemType Directory -Path $staging -Force | Out-Null
Copy-Item *.py $staging -Force
& $python prepare_build_config.py (Join-Path $staging "update_config.json")
if ($LASTEXITCODE -ne 0) { throw "Configuration export failed." }
if ($Channel -eq "Release") {
    $config = Get-Content (Join-Path $staging "update_config.json") -Raw | ConvertFrom-Json
    if (!$config.policy_url -or !$config.allowed_hosts -or !$config.policy_url.StartsWith("https://")) {
        throw "Release requires a public HTTPS update URL. See publisher/README.txt."
    }
}
Copy-Item assets $staging -Recurse -Force
$mode = if ($Channel -eq "Development") { "development" } else { "release" }
Set-Content -Path (Join-Path $staging "build_channel.py") -Value "BUILD_CHANNEL = '$mode'" -Encoding UTF8
$entry = Join-Path $staging "desktop_sparrow.py"
$assetData = (Join-Path $staging "assets") + ";assets"
$configData = (Join-Path $staging "update_config.json") + ";."
& $python -m PyInstaller --noconfirm --clean --windowed --onefile --icon "assets\cat.ico" --name $exeName --add-data $assetData --add-data $configData $entry
if ($LASTEXITCODE -ne 0) { throw "Build failed." }
$portable = Join-Path $PSScriptRoot "portable-release\$Channel"
New-Item -ItemType Directory -Path $portable -Force | Out-Null
Copy-Item "dist\$exeName.exe" $portable -Force
Copy-Item README.txt $portable -Force
& $python -m pip freeze | Set-Content (Join-Path $portable "build-dependencies.txt")
Compress-Archive -Path "$portable\*" -DestinationPath "DesktopCat-$Channel-Windows.zip" -Force
Write-Host "Built dist\$exeName.exe"
if ($Channel -eq "Development") {
    Write-Host "DEVELOPMENT BUILD: no update checks. Do not publish as the release version."
    exit 0
}
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$compiler = if ($iscc) { $iscc.Source } else { "" }
if (!$compiler) {
    $candidate = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) { $compiler = $candidate }
}
if ($compiler) {
    & $compiler installer.iss
    if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }
    Write-Host "Built installer-output\DesktopCat-Setup.exe"
} else {
    Write-Host "Portable release built. Install Inno Setup to also build Setup.exe."
}
