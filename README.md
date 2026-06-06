# SFA3 Widescreen — Android APK

Standalone Android APK that boots directly into **Street Fighter Alpha 3** in
**widescreen 16:9 (448×224)**, built on a customized FBNeo libretro core packaged
inside RetroArch.

This repository holds **only our deltas** (patches, build scripts, assets, docs).
The large upstream trees (FBNeo, RetroArch) stay as separate clones referenced by
the build scripts — they are *not* vendored here.

## Goal

One game, one executable, no ROM picker, custom icon — an APK that launches SFA3
directly with the widescreen viewport.

## Architecture

```
FBNeo (widescreen patch in d_cps2.cpp)  --ndk-build-->  libretro.so  (the core)
                                                            │
RetroArch Android (phoenix)  --gradlew-->  APK  <----------┘  (core + ROM + icon embedded)
                                            │
                                   patch: auto-boot single game
```

## Components / deltas

| Path | What |
|------|------|
| `patches/fbneo-sfa3-widescreen.patch` | FBNeo `d_cps2.cpp`: sfa3 driver 384×224 4:3 → **448×224 16:9** |
| `patches/retroarch-android-build.patch` | RetroArch `build.gradle`: add `mavenCentral()` (jcenter is dead) |
| `patches/retroarch-android-autoboot.patch` | RetroArch `MainMenuActivity`: auto-boot bundled core + ROM (TODO) |
| `scripts/build_core.ps1` | Build the FBNeo core `.so` via NDK r21e |
| `scripts/build_apk.ps1` | Build the RetroArch APK via gradlew + JDK 11 |

## Toolchain (Windows)

| Tool | Version | Location | Notes |
|------|---------|----------|-------|
| NDK (core) | r21e (21.4.7075529) | `E:\android-ndk-r21e` | last NDK supporting `android-18` + `armeabi-v7a`/`x86` of FBNeo's `Application.mk` |
| NDK (RetroArch) | 22.0.7026061 | `E:\android-sdk\ndk\` | pinned by RetroArch `build.gradle` |
| Android SDK | platform-31, build-tools 30.0.3 | `E:\android-sdk` | cmdline-tools |
| JDK (build) | 11.0.31 | `E:\jdk11` | Gradle 6.7.1 / AGP 4.2 need JDK 8–11 (NOT 21) |
| JDK (default) | 21 | system | used only for `sdkmanager` |

### Source clones (not in this repo)

| Repo | Location | Notes |
|------|----------|-------|
| FBNeo (libretro) | `E:\CLAUDE CODE\fbneo-libretro` | contains the widescreen modification |
| RetroArch | `E:\RetroArch` | shallow clone of `libretro/RetroArch` |
| Junction | `E:\fbsrc` → FBNeo | space-free path required by `ndk-build` |

## Gotchas discovered

- **`ndk-build` rejects spaces in paths** → use the `E:\fbsrc` junction.
- **`ndk-build` needs absolute paths** (relative → `jni/jni/..` double-prefix bug).
- **jcenter() is dead** (shut down 2022) → `mavenCentral()` added.
- **Gradle 6.7.1 / AGP 4.2 are incompatible with JDK 21** → build with JDK 11.

## Status

- [x] Brick 1 — FBNeo core `.so` (arm64-v8a) builds and is validated (widescreen baked in)
- [x] Brick 2 — RetroArch APK builds (vanilla validated end-to-end, `BUILD SUCCESSFUL`)
- [x] Embed core (jniLib) + ROM (asset) — APK = 45 MB, arm64-v8a only
- [x] Auto-boot single game patch (`MainMenuActivity.finalStartup`)
- [ ] Custom icon
- [ ] On-device validation (auto-boot + widescreen)

Candidate APK: `out/SFA3-Widescreen.apk`

## How it works (auto-boot)

1. Core shipped as a **jniLib** `lib/arm64-v8a/libfbneo_libretro_android.so`
   → Android extracts it to `nativeLibraryDir` (manifest `extractNativeLibs="true"`).
2. ROM shipped as **asset** `assets/sfa3.zip` → copied to `filesDir/sfa3.zip` on
   first launch by `prepareBundledRom()`.
3. `MainMenuActivity.finalStartup()` launches `RetroActivityFuture` with
   `LIBRETRO` = the jniLib path and `ROM` = the extracted zip → boots straight
   into the game, no picker.
