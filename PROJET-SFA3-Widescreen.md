# Projet — SFA3 Widescreen (Android APK)

> APK Android autonome qui lance **Street Fighter Alpha 3** directement en
> **16:9 (448×224)**, sans redimensionnement « étiré » : le décor existe réellement
> au-delà des 384 px d'origine, on l'affiche, c'est tout.

---

## 1. Objectif

Un seul jeu, un seul exécutable, une icône dédiée. L'utilisateur installe l'APK,
fournit **sa** ROM `sfa3.zip` au 1ᵉʳ lancement, et le jeu démarre en widescreen.
Installable **à côté** de RetroArch officiel (applicationId distinct).

Deux variantes :
| Variante | applicationId | Aspect |
|---|---|---|
| 16:9 | `com.sfa3.widescreen` | 448×224, PAR 16:9 |
| 3:2 | `com.sfa3.widescreen32` | même core, aspect RetroArch forcé (index 7) |

---

## 2. Principe technique du widescreen

CPS2 rend nativement le SFA3 en **384×224 (4:3)**. La tilemap de décor contient
en réalité des colonnes au-delà de 384 px (le moteur n'en affiche qu'une fenêtre).
Il suffit donc d'**élargir la fenêtre de rendu** du driver FBNeo — **aucun patch ROM**,
aucune donnée modifiée.

La modification tient en ~17 lignes dans `src/burn/drv/capcom/d_cps2.cpp` :

```c
#ifndef SFA3_SCRW
#define SFA3_SCRW 448
#define SFA3_ASPX 16
#define SFA3_ASPY 9
#endif
struct BurnDriver BurnDrvCpsSfa3 = {
    ...
    &CpsRecalcPal, 0x1000, SFA3_SCRW, 224, SFA3_ASPX, SFA3_ASPY   // était 384, 224, 4, 3
};
```

Dimensions **paramétrables à la compilation** → un seul code, plusieurs builds
(testé 416 / 448 / 480 / 496 ; 448 retenu). Variante 3:2 :
`-DSFA3_SCRW=432 -DSFA3_ASPX=3 -DSFA3_ASPY=2`.

> FBNeo est un **core monolithique** : tous les ~25 000 jeux compilent dans un seul
> binaire. Il n'existe pas de « core sfa3 » isolé — le delta, c'est ce fichier.

---

## 3. Architecture du paquet

```
FBNeo (patch widescreen d_cps2.cpp)  --ndk-build-->  libfbneo_libretro_android.so  (le core)
                                                          │
RetroArch Android (phoenix)  --gradlew-->  APK  <---------┘   (core + icône, PAS de ROM)
                                            │
                       patch: import ROM au 1er lancement (SAF) + auto-boot du jeu
```

- **Core** livré comme **jniLib** `lib/arm64-v8a/libfbneo_libretro_android.so`
  (Android l'extrait dans `nativeLibraryDir`, manifest `extractNativeLibs="true"`).
- **ROM non incluse** (copyright). Importée par l'utilisateur au 1ᵉʳ lancement.
- **Config** RetroArch pré-réglée (aspect + hotkeys) via `UserPreferences.updateConfigFile`.

---

## 4. Flux « import ROM au 1er lancement » (approche A)

Implémenté dans `MainMenuActivity.java` (patch `retroarch-android-autoboot.patch`) :

1. Au boot, `finalStartup()` vérifie `filesDir/sfa3.zip`.
2. **Absent** → dialogue *« Sélectionne ton sfa3.zip »* → sélecteur de fichiers
   **SAF** (`ACTION_OPEN_DOCUMENT`). On s'arrête là.
3. `onActivityResult` → `importRomFromUri()` copie le fichier choisi vers
   `filesDir/sfa3.zip` (**nom forcé** : FBNeo identifie le set arcade par le nom)
   et vérifie l'entête ZIP `PK\x03\x04`. FBNeo auditera ensuite le romset lui-même.
4. **Présent** → lance `RetroActivityFuture` avec `LIBRETRO` = jniLib et
   `ROM` = `filesDir/sfa3.zip` → boot direct. Lancements suivants : plus de question.

> ⚠️ Règle de build : **ne jamais** mettre de ROM dans
> `pkg/android/phoenix/assets/` — ça la collerait dans l'APK (impubliable).

### Légal
On ne distribue **aucune donnée de jeu**, uniquement l'émulateur/front-end modifié.
L'utilisateur fournit sa propre ROM `sfa3.zip` (CPS2) légalement obtenue.

---

## 5. Hotkeys pré-réglés (manette)

Schéma « Select = modificateur » (seedé si absent, un rebind manuel est préservé) :
| Combo | Action |
|---|---|
| Select + Y | Menu RetroArch |
| Select + L2 | Quick save state |
| Select + R2 | Quick load state |
| Start + Select | Menu RetroArch (filet de sécurité) |

---

## 6. Structure du dépôt (modèle « only our deltas »)

Les gros arbres upstream (FBNeo, RetroArch) **ne sont pas vendorés** ; on garde
seulement nos patchs + scripts + doc.

| Chemin | Rôle |
|---|---|
| `patches/fbneo-sfa3-widescreen.patch` | Le patch widescreen `d_cps2.cpp` |
| `patches/retroarch-android-autoboot.patch` | Import ROM 1er lancement + auto-boot |
| `patches/retroarch-android-build.patch` | `build.gradle` : `mavenCentral()` (jcenter mort) + appId/aspect paramétrables |
| `patches/retroarch-android-hotkeys.patch` | Seed des hotkeys + aspect forcé |
| `patches/fbneo-cps_dump.cpp` + `…-dumpkeys.patch` | Outil d'extraction de stages (sous-projet séparé) |
| `scripts/build_core.ps1` | Build du core `.so` (NDK r21e) |
| `scripts/build_apk.ps1` | Build d'un APK (gradlew + JDK 11) |
| `scripts/build_apks.ps1` | Build **des deux** variantes + contrôle « pas de ROM » + copie vers `out/` |
| `scripts/make_icons.py` | Génère les icônes |
| `README.md` | Doc dev (anglais) |
| `out/*.apk` | APK produits (gitignorés → vont en *Release*) |

---

## 7. Toolchain (Windows)

| Outil | Version | Emplacement | Note |
|---|---|---|---|
| NDK (core) | r21e | `E:\android-ndk-r21e` | dernier NDK gérant `android-18` + abis de l'`Application.mk` de FBNeo |
| NDK (RetroArch) | 22.0.7026061 | `E:\android-sdk\ndk\` | épinglé par le `build.gradle` |
| Android SDK | platform-31, build-tools 30.0.3 | `E:\android-sdk` | |
| JDK (build) | 11 | `E:\jdk11` | Gradle 6.7.1 / AGP 4.2 incompatibles JDK 21 |
| Junction | `E:\fbsrc` → FBNeo | | `ndk-build` refuse les espaces dans les chemins |

### Builder
```powershell
# les deux APK (16:9 + 3:2), sans ROM, copiés dans out/
powershell -ExecutionPolicy Bypass -File scripts\build_apks.ps1
```

Le core (`.so`) n'a besoin d'être rebuildé que si on touche à `d_cps2.cpp` :
`scripts\build_core.ps1`.

---

## 8. Pièges rencontrés

- `ndk-build` refuse les **espaces** dans les chemins → junction `E:\fbsrc`.
- `ndk-build` veut des chemins **absolus** (relatif → bug `jni/jni/..`).
- **jcenter() est mort** (2022) → `mavenCentral()`.
- **Gradle 6.7.1 / AGP 4.2 incompatibles JDK 21** → builder avec JDK 11.
- ROM placée par erreur dans `assets/` → APK gonflé de 23 Mo et **impubliable**
  (le script `build_apks.ps1` refuse désormais de builder dans ce cas).

---

## 9. État

- [x] Core FBNeo `.so` (arm64-v8a) — widescreen intégré, validé
- [x] APK RetroArch buildé end-to-end
- [x] Core embarqué (jniLib), **sans ROM**
- [x] Import ROM au 1ᵉʳ lancement (SAF) + auto-boot
- [x] Variante 3:2
- [x] Icône
- [x] **APK publiables** : `out/SFA3-Widescreen.apk` + `out/SFA3-Widescreen-3-2.apk`
      (22,6 Mo chacun, **0 donnée de jeu** — vérifié)
- [ ] Validation on-device du flux d'import + widescreen
- [x] Publication GitHub : <https://github.com/Rickow/sfa3-widescreen>
      (public, deltas only ; APK en *Release* v1.0, pas dans l'historique)

---

## 10. Publication (fait)

- Dépôt : <https://github.com/Rickow/sfa3-widescreen> — **public**, branche `master`.
- Format : **dépôt de deltas** (patchs + scripts + doc) ; APK en *Release* **v1.0**
  (pas dans l'historique git). Pas de fork du gros arbre FBNeo.
- `gh` installé en portable (`E:\tools\gh\bin\gh.exe`, v2.94) — winget échouait
  (`NO_APPLICABLE_INSTALLER`), zip release GitHub utilisé à la place.
- Reste : validation on-device (seule case ouverte).
```
