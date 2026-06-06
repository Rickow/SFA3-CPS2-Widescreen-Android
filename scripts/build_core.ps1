# Build the FBNeo libretro core (.so) with the SFA3 widescreen patch baked in.
# Usage: powershell -ExecutionPolicy Bypass -File build_core.ps1 [ABI]
#   ABI defaults to arm64-v8a. Other values: armeabi-v7a x86 x86_64
#
# Requires:
#   - NDK r21e at E:\android-ndk-r21e
#   - Junction E:\fbsrc -> E:\CLAUDE CODE\fbneo-libretro  (ndk-build rejects spaces)
#     New-Item -ItemType Junction -Path E:\fbsrc -Target "E:\CLAUDE CODE\fbneo-libretro"

param([string]$Abi = "arm64-v8a")

$ndk  = "E:\android-ndk-r21e"
$proj = "E:\fbsrc\src\burner\libretro"   # space-free junction
$out  = Join-Path $PSScriptRoot "..\out"

if (-not (Test-Path $proj)) {
    Write-Error "Junction E:\fbsrc missing. Create it:`n  New-Item -ItemType Junction -Path E:\fbsrc -Target `"E:\CLAUDE CODE\fbneo-libretro`""
    exit 1
}

# Absolute paths are mandatory (relative -> jni/jni/.. double-prefix bug).
& "$ndk\ndk-build.cmd" `
    NDK_PROJECT_PATH="$proj" `
    APP_BUILD_SCRIPT="$proj\jni\Android.mk" `
    NDK_APPLICATION_MK="$proj\jni\Application.mk" `
    APP_ABI=$Abi -j8
if ($LASTEXITCODE -ne 0) { Write-Error "ndk-build failed"; exit 1 }

New-Item -ItemType Directory -Force -Path $out | Out-Null
$so = "$proj\libs\$Abi\libretro.so"
Copy-Item $so (Join-Path $out "fbneo_libretro_android.so") -Force
Write-Output "OK -> out\fbneo_libretro_android.so ($Abi)"
