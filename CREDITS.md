# Credits & licences

This repository holds **only our deltas** (patches, build scripts, docs). All emulation
credit belongs to the upstream authors. Thank you.

## Upstream components

| Component | Role | License |
|---|---|---|
| **[FBNeo](https://github.com/libretro/FBNeo)** (FinalBurn Neo, libretro) | CPS-2 emulation core — patched (`d_cps2.cpp`) for 448×224 16:9 | FB Alpha / FBNeo license (**non-commercial**) |
| **[RetroArch](https://github.com/libretro/RetroArch)** (Android / phoenix) | frontend packaged as the APK — patched for first-run ROM import + auto-boot | GPL-3.0 |
| **[Android NDK](https://developer.android.com/ndk)** / Gradle | build toolchain (core `.so` + APK) | build tools only |

The large upstream trees (FBNeo, RetroArch) are **not** vendored here — the build scripts
reference them as separate clones.

## Licence of this repository

The patches derive from **RetroArch (GPL-3.0)**, so this repository's deltas are released
under **[GPL-3.0](LICENSE)**.

⚠️ **Non-commercial**: the CPS-2 core is **FBNeo / FB Alpha**, whose license forbids
commercial use. The resulting APK as a whole is therefore for **non-commercial** use.

## ⚠️ What is NOT provided (and never will be)

- **No ROM / game data** — Street Fighter Alpha 3 is © **Capcom**. The APK ships no game
  data; on first launch it asks you to pick **your own** `sfa3.zip` (CPS-2 romset).

"Street Fighter" and "Capcom" are trademarks of Capcom. This project is neither affiliated
with nor endorsed by Capcom.

## Original tooling — MIT

The RetroArch / FBNeo **patches** in this repository are derivative works and keep their
upstream licenses (RetroArch **GPL-3.0**; the CPS-2 core **FBNeo / FB Alpha**, whose license
is **non-commercial**). Our own standalone build tooling (`scripts/`) is offered under the
**MIT License** — do whatever you want with it.
