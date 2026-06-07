# Build the RetroArch Android APK (aarch64 flavor) with JDK 11.
# Usage: powershell -ExecutionPolicy Bypass -File build_apk.ps1 [task]
#   task defaults to assembleAarch64Release.
#
# Requires:
#   - Android SDK at E:\android-sdk (platform-31, build-tools 30.0.3, ndk 22.0.7026061)
#   - JDK 11 at E:\jdk11  (Gradle 6.7.1 / AGP 4.2 are NOT compatible with JDK 21)
#   - E:\RetroArch\pkg\android\phoenix\local.properties -> sdk.dir=E:\\android-sdk

param(
    [string]$Task    = "assembleAarch64Release",
    [string]$AppId   = "",   # ex variante 3:2 : "com.sfa3.widescreen32"
    [string]$AppName = ""    # ex : "SFA3 3:2"
)

$env:JAVA_HOME = "E:\jdk11"
$env:ANDROID_SDK_ROOT = "E:\android-sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

$gArgs = @($Task, "--stacktrace")
if ($AppId   -ne "") { $gArgs += "-PAPP_ID=$AppId" }
if ($AppName -ne "") { $gArgs += "-PAPP_NAME=$AppName" }

Set-Location "E:\RetroArch\pkg\android\phoenix"
& .\gradlew.bat @gArgs
if ($LASTEXITCODE -ne 0) { Write-Error "gradle build failed"; exit 1 }

Write-Output "=== APKs produced ==="
Get-ChildItem -Recurse -Filter *.apk build\outputs\apk 2>$null | ForEach-Object { $_.FullName }
