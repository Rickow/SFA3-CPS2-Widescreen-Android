# Build BOTH publishable APKs (no ROM bundled): 16:9 default + 3:2 variant.
# Reuses the existing widescreen core jniLib (only the Android Java changed).
# Usage: powershell -ExecutionPolicy Bypass -File build_apks.ps1
#
# Requires JDK 11 (E:\jdk11), Android SDK (E:\android-sdk), and
#   E:\RetroArch\pkg\android\phoenix\local.properties -> sdk.dir=E:\\android-sdk

$ErrorActionPreference = "Stop"

$env:JAVA_HOME = "E:\jdk11"
$env:ANDROID_SDK_ROOT = "E:\android-sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

$phoenix = "E:\RetroArch\pkg\android\phoenix"
$outDir  = "E:\CLAUDE CODE\sfa3-widescreen-android\out"
New-Item -ItemType Directory -Force $outDir | Out-Null

# Safety: refuse to build if a ROM got into assets/ (would make the APK non-distributable).
if (Test-Path "$phoenix\assets\sfa3.zip") {
    Write-Error "REFUS: $phoenix\assets\sfa3.zip present -> l'APK contiendrait la ROM. Retire-le."
    exit 1
}

Set-Location $phoenix

function Build-Variant($apkLabel, $extraArgs) {
    Write-Output "=== BUILD $apkLabel ==="
    $a = @("assembleAarch64Release", "--stacktrace") + $extraArgs
    & .\gradlew.bat @a
    if ($LASTEXITCODE -ne 0) { Write-Error "gradle build failed ($apkLabel)"; exit 1 }
    $apk = Get-ChildItem -Recurse -Filter *.apk "build\outputs\apk" |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $apk) { Write-Error "no APK produced ($apkLabel)"; exit 1 }
    Copy-Item -Force $apk.FullName "$outDir\$apkLabel"
    Write-Output "-> $outDir\$apkLabel ($([math]::Round($apk.Length/1MB,1)) MB)"
}

# Clean once so no stale (ROM-bearing) merged assets survive.
& .\gradlew.bat clean --stacktrace
if ($LASTEXITCODE -ne 0) { Write-Error "gradle clean failed"; exit 1 }

# 16:9 default (ASPECT omitted -> follows core's 16:9)
Build-Variant "SFA3-Widescreen.apk" @()

# 3:2 variant (distinct appId/name, force RetroArch aspect index 7 = 3:2)
Build-Variant "SFA3-Widescreen-3-2.apk" @("-PAPP_ID=com.sfa3.widescreen32", "-PAPP_NAME=SFA3 3:2", "-PASPECT=7")

Write-Output "=== DONE ==="
Get-ChildItem $outDir -Filter *.apk | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
