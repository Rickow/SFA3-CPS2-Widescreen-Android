# SFA3 Widescreen — APK Android

> 🌐 [English](README.md) · **Français**

APK Android autonome qui démarre directement sur **Street Fighter Alpha 3** en
**16:9 (448×224)**, basé sur un core FBNeo libretro modifié et empaqueté dans RetroArch.

Ce dépôt ne contient **que nos deltas** (patches, scripts de build, ressources, docs).
Les gros arbres amont (FBNeo, RetroArch) restent des clones séparés référencés par les
scripts de build — ils ne sont *pas* embarqués ici.

## Objectif

Un jeu, un exécutable, une icône dédiée — un APK qui lance SFA3 directement avec le
cadrage widescreen. L'APK embarque **tout sauf la ROM** : au premier lancement il te
demande de choisir **ta propre** `sfa3.zip`, la copie dans l'app, puis démarre droit
dans le jeu. Aucune ROM n'est redistribuée.

> **Légal :** Street Fighter Alpha 3 est © Capcom. Ce projet ne distribue **aucune
> donnée de jeu** — seulement l'émulateur/front-end modifié. Tu dois fournir ta propre
> `sfa3.zip` (romset CPS2) obtenue légalement.

## Architecture

```
FBNeo (patch widescreen dans d_cps2.cpp)  --ndk-build-->  libretro.so  (le core)
                                                              │
RetroArch Android (phoenix)  --gradlew-->  APK  <------------┘  (core + icône embarqués, PAS de ROM)
                                            │
                    patch : import ROM au 1er lancement (SAF) + auto-boot du jeu unique
```

## Composants / deltas

| Chemin | Quoi |
|------|------|
| `patches/fbneo-sfa3-widescreen.patch` | FBNeo `d_cps2.cpp` : driver sfa3 384×224 4:3 → **448×224 16:9** |
| `patches/retroarch-android-build.patch` | RetroArch `build.gradle` : ajout de `mavenCentral()` (jcenter est mort) |
| `patches/retroarch-android-autoboot.patch` | RetroArch `MainMenuActivity` : import ROM au 1er lancement (sélecteur SAF → copie vers `filesDir/sfa3.zip`) + auto-boot du jeu unique (aucune ROM embarquée) |
| `scripts/build_core.ps1` | Build du core FBNeo `.so` via NDK r21e |
| `scripts/build_apk.ps1` | Build de l'APK RetroArch via gradlew + JDK 11 |

## Chaîne d'outils (Windows)

| Outil | Version | Emplacement | Notes |
|------|---------|----------|-------|
| NDK (core) | r21e (21.4.7075529) | `E:\android-ndk-r21e` | dernier NDK gérant `android-18` + `armeabi-v7a`/`x86` du `Application.mk` de FBNeo |
| NDK (RetroArch) | 22.0.7026061 | `E:\android-sdk\ndk\` | figé par le `build.gradle` de RetroArch |
| Android SDK | platform-31, build-tools 30.0.3 | `E:\android-sdk` | cmdline-tools |
| JDK (build) | 11.0.31 | `E:\jdk11` | Gradle 6.7.1 / AGP 4.2 exigent JDK 8–11 (PAS 21) |
| JDK (défaut) | 21 | système | utilisé seulement pour `sdkmanager` |

### Clones sources (pas dans ce dépôt)

| Dépôt | Emplacement | Notes |
|------|----------|-------|
| FBNeo (libretro) | `E:\CLAUDE CODE\fbneo-libretro` | contient la modification widescreen |
| RetroArch | `E:\RetroArch` | clone superficiel de `libretro/RetroArch` |
| Jonction | `E:\fbsrc` → FBNeo | chemin sans espace requis par `ndk-build` |

## Pièges rencontrés

- **`ndk-build` refuse les espaces dans les chemins** → utiliser la jonction `E:\fbsrc`.
- **`ndk-build` exige des chemins absolus** (relatif → bug de double préfixe `jni/jni/..`).
- **jcenter() est mort** (fermé en 2022) → `mavenCentral()` ajouté.
- **Gradle 6.7.1 / AGP 4.2 incompatibles avec JDK 21** → builder avec JDK 11.

## État

- [x] Brique 1 — le core FBNeo `.so` (arm64-v8a) compile et est validé (widescreen intégré)
- [x] Brique 2 — l'APK RetroArch compile (vanilla validé de bout en bout, `BUILD SUCCESSFUL`)
- [x] Core embarqué (jniLib) — APK arm64-v8a seul, **aucune ROM embarquée**
- [x] Patch auto-boot du jeu unique (`MainMenuActivity.finalStartup`)
- [x] Import ROM au 1er lancement via sélecteur SAF (l'utilisateur fournit sa `sfa3.zip`)
- [x] Icône personnalisée
- [ ] Validation sur appareil (import au 1er lancement + auto-boot + widescreen)

APK distribuable : `out/SFA3-Widescreen.apk` (publiable — ne contient aucune donnée de jeu)

## Fonctionnement (import au 1er lancement + auto-boot)

1. Le core est livré en **jniLib** `lib/arm64-v8a/libfbneo_libretro_android.so`
   → Android l'extrait vers `nativeLibraryDir` (manifest `extractNativeLibs="true"`).
2. **Aucune ROM n'est embarquée.** Au 1er lancement, `MainMenuActivity.finalStartup()`
   vérifie `filesDir/sfa3.zip` ; si absente, il ouvre un sélecteur Storage Access
   Framework (`ACTION_OPEN_DOCUMENT`) pour demander ta `sfa3.zip`.
3. `importRomFromUri()` copie le fichier choisi vers `filesDir/sfa3.zip` (nom forcé —
   FBNeo identifie le set arcade par le nom de fichier) et vérifie l'en-tête ZIP
   `PK\x03\x04`. FBNeo audite lui-même le romset au chargement.
4. Une fois présente, `finalStartup()` lance `RetroActivityFuture` avec `LIBRETRO` = le
   chemin de la jniLib et `ROM` = `filesDir/sfa3.zip` → démarre droit dans le jeu.
   Les lancements suivants sautent le sélecteur et démarrent directement.

> **Note de build :** ne jamais placer de ROM dans `pkg/android/phoenix/assets/` — cela
> l'intégrerait à l'APK et rendrait le build non distribuable.

---

## Crédits & licence

Deltas sous **[GPL-3.0](LICENSE)** (les patches dérivent de RetroArch). Liste complète des
composants, liens GitHub et licences dans **[CREDITS.md](CREDITS.md)**.

⚠️ Le core CPS-2 est **FBNeo** (non commercial) → l'APK est à usage **non commercial**.
Aucune ROM / donnée de jeu n'est distribuée (Street Fighter Alpha 3 © Capcom).
