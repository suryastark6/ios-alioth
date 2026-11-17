# alioth test session on Windows: one menu for the steps in docs/FIRST-BOOT.md.
#
# Run it with alioth-session.bat (double-click). Expected layout:
#   <folder>\alioth-session.bat, alioth-session.ps1   (this script)
#   <folder>\ios-alioth\                               (the repository)
#   <folder>\out\                                      (test images)
#   <folder>\logs\                                     (written here)
# Everything shown on screen is also written to logs\session-<time>.txt.
# Nothing is ever flashed: phone images are only started with
# "fastboot boot", and "fastboot reboot" returns to Android.

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Join-Path $Root 'ios-alioth'
$Out = Join-Path $Root 'out'
$Logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
Start-Transcript -Path (Join-Path $Logs "session-$Stamp.txt") | Out-Null

function Find-Tool($name) {
    $cmd = Get-Command "$name.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($d in @('C:\platform-tools', "$env:USERPROFILE\platform-tools",
                     "$env:LOCALAPPDATA\Android\Sdk\platform-tools", "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools",
                     (Join-Path $Root 'platform-tools'))) {
        $p = Join-Path $d "$name.exe"
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Find-Python {
    foreach ($n in @('python', 'py', 'python3')) {
        $cmd = Get-Command "$n.exe" -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { return $cmd.Source }
    }
    return $null
}

function Run($exe, [string[]]$argv) {
    Write-Host "> $(Split-Path -Leaf $exe) $($argv -join ' ')" -ForegroundColor Cyan
    & $exe @argv 2>&1 | ForEach-Object { "$_" } | Out-Host
    Write-Host "(exit $LASTEXITCODE)"
}

$Adb = Find-Tool 'adb'
$Fastboot = Find-Tool 'fastboot'
$Python = Find-Python
$Git = (Get-Command 'git.exe' -ErrorAction SilentlyContinue).Source

Write-Host "alioth session $Stamp"
Write-Host "folder   : $Root"
Write-Host "adb      : $(if ($Adb) { $Adb } else { 'NOT FOUND' })"
Write-Host "fastboot : $(if ($Fastboot) { $Fastboot } else { 'NOT FOUND' })"
Write-Host "python   : $(if ($Python) { $Python } else { 'NOT FOUND' })"
Write-Host "git      : $(if ($Git) { $Git } else { 'not found (repository update skipped)' })"
if ($Adb) { Run $Adb @('version') }
if ($Fastboot) { Run $Fastboot @('--version') }
if ($Git -and (Test-Path (Join-Path $Repo '.git'))) {
    Write-Host "`nUpdating the repository..."
    Run $Git @('-C', $Repo, 'pull', '--ff-only')
    Run $Git @('-C', $Repo, 'log', '--oneline', '-1')
}
if (Test-Path (Join-Path $Out 'BUILD.txt')) { Get-Content (Join-Path $Out 'BUILD.txt') | Out-Host }

function Check-Fastboot {
    if (-not $Fastboot) { Write-Host 'fastboot not found: install platform-tools to C:\platform-tools'; return $false }
    $devs = & $Fastboot devices 2>&1
    Write-Host "fastboot devices: $devs"
    if (-not "$devs".Trim()) {
        Write-Host 'No phone in fastboot. Hold Volume Down + Power until FASTBOOT shows, connect USB, try again.' -ForegroundColor Yellow
        return $false
    }
    return $true
}

function Boot-Image($name) {
    $img = Join-Path $Out $name
    if (-not (Test-Path $img)) { Write-Host "missing $img" -ForegroundColor Red; return }
    if (-not (Check-Fastboot)) { return }
    $h = (Get-FileHash -Algorithm SHA256 $img).Hash.ToLower()
    Write-Host "$name sha256 $h"
    Run $Fastboot @('boot', $img)
    Write-Host "`nWatch the phone now and take photos (see docs\FIRST-BOOT.md)." -ForegroundColor Green
    Write-Host 'If it is stuck for more than 5 minutes: hold Power + Volume Down until it restarts into fastboot.'
}

while ($true) {
    Write-Host ''
    Write-Host '=============== alioth session ==============='
    Write-Host ' 1  Check the phone (in fastboot): unlocked, model, slot'
    Write-Host ' 2  Boot OrangeFox recovery (temporary, nothing flashed)'
    Write-Host ' 3  Backup + hardware scan (phone in OrangeFox)'
    Write-Host ' 4  Reboot from recovery to fastboot'
    Write-Host ' 5  M1 test: shim display probe (alioth-m1-v3.img)'
    Write-Host ' 6  M3 test: start XNU (alioth-m3-v3.img)'
    Write-Host ' 7  Back to Android (fastboot reboot)'
    Write-Host ' 8  Show connected devices (adb + fastboot)'
    Write-Host ' 0  Quit'
    $c = Read-Host 'Choose'
    Write-Host "choice: $c"
    switch ($c) {
        '1' {
            if (Check-Fastboot) {
                foreach ($v in @('unlocked', 'product', 'current-slot', 'version-bootloader', 'slot-count', 'is-userspace')) {
                    Run $Fastboot @('getvar', $v)
                }
            }
        }
        '2' {
            if (-not (Check-Fastboot)) { break }
            $fox = Get-ChildItem -Path $Root -Filter '*.img' -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match 'orangefox|ofox|twrp|recovery' } | Select-Object -First 1
            if ($fox) { $path = $fox.FullName; Write-Host "found $path" }
            else { $path = (Read-Host 'Path to the OrangeFox .img (drag the file here)').Trim('"') }
            if (Test-Path $path) { Run $Fastboot @('boot', $path); Write-Host 'Wait for the OrangeFox home screen (cancel any PIN prompt), then choose 3.' }
            else { Write-Host "not found: $path" -ForegroundColor Red }
        }
        '3' {
            if (-not $Adb -or -not $Python) { Write-Host 'adb and python are both needed' -ForegroundColor Red; break }
            Run $Adb @('devices')
            Run $Python @((Join-Path $Repo 'tools\alioth-backup.py'), '--adb', $Adb)
            Write-Host "`nCopy $Repo\backup to a second place (it holds IMEI/calibration partitions)." -ForegroundColor Yellow
        }
        '4' { if ($Adb) { Run $Adb @('reboot', 'bootloader') } }
        '5' { Boot-Image 'alioth-m1-v3.img' }
        '6' { Boot-Image 'alioth-m3-v3.img' }
        '7' { if (Check-Fastboot) { Run $Fastboot @('reboot') } }
        '8' { if ($Adb) { Run $Adb @('devices', '-l') }; if ($Fastboot) { Run $Fastboot @('devices', '-l') } }
        '0' { Stop-Transcript | Out-Null; exit 0 }
        default { Write-Host 'Type a number from the menu.' }
    }
}
