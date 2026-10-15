param([ValidateSet("Development","Release")][string]$Channel="Development")
$ErrorActionPreference = "Stop"
$appName = if ($Channel -eq "Development") { "DesktopCatDev" } else { "DesktopCat" }
$exeName = if ($Channel -eq "Development") { "DesktopCat-Dev-v0.4.5.exe" } else { "DesktopCat-v0.4.5.exe" }
$sourceExe = Join-Path $PSScriptRoot "dist\$exeName"
if (!(Test-Path $sourceExe)) {
    throw "Build the matching Development or Release EXE first."
}
$installDir = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "$appName"
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
$targetExe = Join-Path $installDir "DesktopCat.exe"
$targetIcon = Join-Path $installDir "cat.ico"
Copy-Item $sourceExe $targetExe -Force
Copy-Item (Join-Path $PSScriptRoot "assets\cat.ico") $targetIcon -Force
$shell = New-Object -ComObject WScript.Shell
$desktop = $shell.SpecialFolders.Item("Desktop")
$shortcut = $shell.CreateShortcut((Join-Path $desktop "$appName.lnk"))
$shortcut.TargetPath = $targetExe
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$targetIcon,0"
$shortcut.Description = "Desktop Cat"
$shortcut.Save()
Write-Host "DesktopCat shortcut created on your Desktop."
Write-Host "Double-click the cat icon to open the app."
