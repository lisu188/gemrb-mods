# GemRB Android Modernization Design

Status: Draft

Target upstream: `gemrb/gemrb` master

Initial development target: Android arm64-v8a

## Goal

Restore GemRB as a first-class Android application using the current GemRB codebase and current Android tooling, without carrying forward the obsolete Ant/ndk-build/Python 2 Android packaging layer.

The first milestone is deliberately narrow: produce a debuggable `arm64-v8a` APK that starts SDL2, initializes GemRB and embedded Python 3, loads packaged GemRB runtime data, and reaches the GemRB demo or launcher shell. Game import, complete audio support and additional ABIs come after that boot path is stable.

## Current state

The upstream repository still contains Android-specific entry points and CMake handling, but its Android packaging code is legacy infrastructure.

The existing Android build assumes:

- Ant
- `ndk-build`
- obsolete Android SDK tooling
- `gnustl_static`
- Python 2.6
- `armeabi`
- direct `/sdcard` paths
- old SDL Android project layouts

These assumptions are incompatible with a modern Android toolchain.

The useful upstream pieces are:

- `platforms/android/GemRB.cpp`
- `platforms/android/AndroidLogger.cpp`
- the `ANDROID` branch in GemRB CMake
- SDL2 backend support
- static plugin linking support
- existing runtime data layout (`GUIScripts`, `override`, `unhardcoded`)

## Design principles

1. Keep the GemRB core platform-neutral.
2. Keep Android-specific code thin.
3. Use Gradle only for Android packaging and lifecycle integration.
4. Use CMake for native code.
5. Use SDL2 as the Android activity/input/windowing layer.
6. Link GemRB plugins statically on Android.
7. Embed Python 3 using the official Android Python distribution where practical.
8. Do not rely on unrestricted external storage.
9. Build one ABI first (`arm64-v8a`).
10. Make CI produce an installable debug APK early.

## Proposed architecture

```text
Android application
    |
    v
SDLActivity / GemRBActivity
    |
    v
libSDL2.so
    |
    v
libmain.so
    |
    +-- GemRB executable entry point
    +-- gemrb_core
    +-- statically linked GemRB plugins
    +-- Python embedding bridge
    |
    +-- libpython3.x.so
    +-- optional native dependencies

APK assets
    |
    +-- GemRB runtime data
    |     +-- GUIScripts
    |     +-- override
    |     +-- unhardcoded
    |
    +-- Python standard library payload

App-private files directory
    |
    +-- extracted GemRB runtime data
    +-- extracted Python runtime
    +-- imported game installations
    +-- cache
    +-- saves/configuration
```

## Native target model

SDL's Android model expects the application entry point to be provided by a shared library. GemRB's current Android CMake branch creates an executable, so Android should instead produce a shared target named `main` (or a target whose output name is `main`).

Conceptually:

```cmake
ELSEIF(ANDROID)
    ADD_LIBRARY(gemrb SHARED
        ${PLATFORM_DIR}/android/GemRB.cpp
        ${PLATFORM_DIR}/android/AndroidLogger.cpp
    )
    SET_TARGET_PROPERTIES(gemrb PROPERTIES OUTPUT_NAME main)
ELSE()
    ADD_EXECUTABLE(gemrb GemRB.cpp)
ENDIF()
```

The exact patch must preserve desktop and other platform behavior unchanged.

## Plugin model

Android should use `STATIC_LINK=ON`.

Reasons:

- avoids runtime discovery of plugin `.so` files inside APK/application storage
- reduces Android-specific loader logic
- simplifies packaging
- simplifies startup diagnostics
- gives one primary GemRB native binary to inspect

GemRB already has static-link support using whole-archive semantics, so this should be an adaptation rather than a new plugin architecture.

## Android project

Create a new modern Android project rather than incrementally repairing the Ant project.

Proposed location:

```text
platforms/android/
    app/
    gradle/
    build.gradle.kts
    settings.gradle.kts
    gradle.properties
    README.md
```

Legacy files should remain until the new port boots reliably, then be removed or moved under a `legacy/` directory in a separate cleanup change.

Initial Android configuration:

- compileSdk: current stable SDK
- targetSdk: current stable SDK
- minSdk: 28 initially
- ABI: `arm64-v8a`
- NDK: current stable NDK
- C++ runtime: libc++
- build types: debug, release

The minSdk value can be revisited later. API 28 is a useful initial boundary because it simplifies libc/iconv availability and avoids spending the first milestone on compatibility work for older devices.

## SDL integration

Use SDL2's maintained Android Gradle project structure as the reference implementation.

Responsibilities retained by SDL:

- activity lifecycle
- surface creation
- native main bootstrap
- touch/mouse/keyboard/controller event forwarding
- audio-device integration where applicable
- orientation/window setup

GemRB-specific Java/Kotlin should only contain behavior SDL does not provide, such as game-directory import and first-run runtime extraction.

## Python 3 embedding

Python is required by GemRB and is the largest packaging dependency.

Proposed strategy:

1. Package `libpython3.x.so` per ABI under `jniLibs` or import it as a CMake target.
2. Package the standard library as an application asset payload.
3. Extract the runtime into the app-private files directory on first launch or application-version change.
4. Set Python home/search paths before GemRB initializes GUIScript.
5. Do not execute Python directly out of compressed APK assets.

Expected layout:

```text
files/runtime/python/
    lib/
    python3.x/
```

A small manifest should record the runtime payload version to allow deterministic upgrades.

## GemRB runtime assets

Package:

```text
GUIScripts/
override/
unhardcoded/
```

as Android assets and extract them to app-private storage.

Expected layout:

```text
files/runtime/gemrb/GUIScripts
files/runtime/gemrb/override
files/runtime/gemrb/unhardcoded
```

`GEMRB_DATA` should point at this extracted runtime root.

Do not couple these files to the game installation path.

## Storage model

Avoid legacy `/sdcard/gemrb/...` assumptions.

Three storage classes should be kept separate:

### 1. Application runtime

App-private and managed entirely by the application.

```text
files/runtime/
```

### 2. Game installations

Initial implementation: import/copy a selected Infinity Engine installation into app-managed storage.

```text
files/games/<game-id>/
```

A later optimization may support direct access through Android's Storage Access Framework where GemRB's file access patterns make that practical.

### 3. Saves and configuration

```text
files/user/<game-id>/
```

This prevents upgrades of engine/runtime files from touching saves.

## Game import

First production-quality UI feature after booting the engine:

1. User chooses a game directory using `ACTION_OPEN_DOCUMENT_TREE`.
2. Android code validates the selected directory using recognizable Infinity Engine files.
3. Files are copied/imported into app-managed storage.
4. A game profile is written.
5. GemRB starts using that profile.

Do not request all-files access.

Potential optimization later: persist URI permissions and provide a VFS bridge, but copying first is substantially simpler and safer.

## Configuration model

Long-term Android should not require users to manually edit `GemRB.cfg` with ADB.

Proposed model:

```text
Android preferences / game profile
        |
        v
Generated GemRB configuration
        |
        v
GemRB startup
```

The generated config remains a normal GemRB config file so Android does not create a parallel engine configuration system.

## Dependencies

Bring dependencies up incrementally.

### Milestone A: boot

- SDL2
- zlib
- Python 3
- iconv/libc support
- GemRB core
- static GemRB plugins required for demo startup

Disable where possible:

- OpenAL
- SDL_mixer
- VLC
- Vorbis
- FreeType
- PNG
- OpenGL/GLES-specific GemRB backend

### Milestone B: useful UI

Enable:

- FreeType
- PNG

### Milestone C: game audio

Prefer OpenAL Soft as the first complete audio backend.

Enable:

- OpenAL Soft
- Vorbis

SDL_mixer can remain optional.

### Milestone D: graphics optimization

Evaluate GemRB GLES/OpenGL backend only after the SDL2 renderer path is stable and benchmarked.

## Logging and diagnostics

Android logging must be usable from the first commit.

Requirements:

- GemRB log messages visible through logcat
- startup stages have explicit markers
- native crashes symbolizable from CI artifacts
- log file written under app-private storage
- startup errors surfaced to Java/Kotlin UI rather than only terminating the process

Useful startup markers:

```text
ANDROID_BOOT
SDL_READY
RUNTIME_ASSETS_READY
PYTHON_READY
GEMRB_CORE_READY
GUI_SCRIPT_READY
GAME_PROFILE_READY
MAIN_LOOP_ENTERED
```

## CI

Add an Android GitHub Actions job early.

The job should:

1. install JDK
2. install Android SDK/NDK
3. configure Gradle cache
4. build `assembleDebug`
5. upload the APK
6. upload native symbols

Later add an emulator smoke test that launches the app and checks for `MAIN_LOOP_ENTERED` in logcat.

CI should initially build only `arm64-v8a` unless emulator testing requires `x86_64`.

## Proposed implementation sequence

### Phase 0 — architecture

- document decisions
- identify required upstream CMake changes
- define minimum dependency set
- define Android file/runtime layout

### Phase 1 — Gradle/SDL shell

- add modern Android project
- launch SDL activity
- compile trivial native `libmain.so`
- produce/install APK

Exit criterion: app launches and native `main()` executes.

### Phase 2 — GemRB core

- convert Android GemRB target to shared-library model
- enable static plugin linking
- compile core with Android NDK

Exit criterion: GemRB reaches early engine initialization.

### Phase 3 — Python/runtime assets

- package Python shared library
- extract Python stdlib
- extract GemRB runtime data
- configure search paths

Exit criterion: GUIScript initializes successfully.

### Phase 4 — demo boot

- package or acquire demo data
- generate startup config
- fix Android-specific file/path assumptions

Exit criterion: GemRB demo reaches interactive main loop.

### Phase 5 — game import

- implement Storage Access Framework directory selection
- validation/import pipeline
- game profile model

Exit criterion: imported BG/IWD/PST installation reaches game UI.

### Phase 6 — audio and rendering

- OpenAL Soft
- Vorbis
- optional GLES investigation

### Phase 7 — compatibility

- add `x86_64` for emulator/ChromeOS if useful
- evaluate lower minSdk
- Android lifecycle regression fixes
- suspend/resume/audio focus
- controller/touch UX

## First code changes to target

1. Add new Gradle project under `platforms/android`.
2. Change the CMake Android target from executable to shared library.
3. Make the Android target compatible with `STATIC_LINK=ON`.
4. Add an Android CMake preset/toolchain entry or Gradle CMake invocation.
5. Add runtime asset extraction helper.
6. Add Python runtime location configuration.
7. Add Android CI job.

## Explicit non-goals for the first milestone

- Play Store publishing
- backward compatibility with the old Ant project
- supporting every ABI
- supporting Android versions below API 28
- direct execution from arbitrary external-storage folders
- launcher UX polish
- GLES optimization
- complete audio stack

## Open design questions

1. Keep SDL2 or move directly to SDL3?
   - Recommendation for initial revival: SDL2, because GemRB already uses it and changing SDL major versions would mix two migrations.

2. Copy game installations or implement a SAF-backed VFS?
   - Recommendation: copy/import first. SAF VFS can be evaluated later.

3. Python version pinning strategy?
   - Recommendation: pin one Python minor version per GemRB Android release and upgrade intentionally.

4. Keep Android inside upstream GemRB or use a companion repository?
   - Recommendation: keep the maintained build in upstream GemRB so Android-specific CMake changes and engine compatibility cannot drift.

5. Remove legacy Android code immediately?
   - Recommendation: no. Remove it only after the modern APK boots in CI.

## Definition of the first meaningful milestone

A successful first milestone is not "CMake compiles on Android". It is:

- `./gradlew assembleDebug` succeeds from a clean checkout
- the APK installs on a current Android device
- SDL activity launches
- GemRB native entry point executes
- GemRB runtime assets are available
- Python initializes
- GUIScript initializes
- the GemRB demo reaches an interactive main loop
- logcat contains deterministic startup markers

Everything after that is feature restoration rather than resurrection of the build system.
