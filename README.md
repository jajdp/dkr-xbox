# Diddy Kong Racing on Xbox — the UWP port

How to take [Golden Balloon](https://github.com/akratch/goldenballoon), the native source port of
*Diddy Kong Racing* (N64, 1997), and run it **on an Xbox Series in Developer Mode**, as a UWP
package you build and sign yourself.

*(Español: [README.es.md](README.es.md))*

No UWP build of this game existed, so the port was written from scratch: there is no second CMake
project and no duplicated tree. It plays — intro, menus, adventure mode, Taj's first challenge
won with a controller.

## What this repository is

**A recipe and the tools that apply it**, to your own checkout, on your own machine:

| | |
|---|---|
| `src/` | The WinRT entry point and the UWP compatibility layer — 533 lines, all first-party |
| `tools/` | Five patches, the builder, the packer and the verifier — [index](tools/README.md) |
| `package/` | The package manifest |
| `docs/` | How to build it, and why it is shaped this way |

## What this repository is **not**

It contains **no ROM, no game assets, no built executable, no `.msix` package and no artwork**.
It cannot produce a playable game on its own, and nothing you can download here is a game. You
need your own legally dumped ROM and a working build of Golden Balloon first. See
[`NOTICE.md`](NOTICE.md).

The nine package tiles are not here either: the ones on the real console were made from the
game's cover art. You supply your own — [`docs/ASSETS.md`](docs/ASSETS.md) lists the exact sizes,
and the packer stops with a clear message if any is missing.

## What makes it sustainable

**It translates the desktop build instead of maintaining a second one.** The object list comes
from `build.ninja` and each compile command from `compile_commands.json`; every one is translated
into the console's dialect and re-run. A file the upstream adds appears on its own — which
matters, because this port was written against `v1.7.0` and the release before it was four weeks
old.

## What you need first

| | |
|---|---|
| The game project | [akratch/goldenballoon](https://github.com/akratch/goldenballoon) `v1.7.0`, **building and running on your PC first** |
| Your own ROM | Revision **1.1** — in the usual sets, the one marked "(Rev A)". The 1.0 is rejected |
| Visual Studio | With the C++ desktop tools, plus the Windows 10/11 SDK. The version is not pinned and the UWP workload is not needed — [`docs/INSTALL.md`](docs/INSTALL.md) §1 |
| PowerShell | The one Windows already ships: **PowerShell 7 is not needed**. The commands carry `-ExecutionPolicy Bypass` because a stock Windows will not run a `.ps1` without it |
| llvm-mingw, Dawn for UWP, SDL2 built for WinRT | Where each comes from, and why that one: [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) |
| An Xbox in Developer Mode | And a certificate to sign with — a self-signed one is fine |

## How it goes

Three commands. [`docs/INSTALL.md`](docs/INSTALL.md) §0 covers the terminal at more length, and
the rest of that guide is the long version of these three lines.

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
# 1. patch your checkout (idempotent, all-or-nothing, nothing is deleted)
python tools\apply_uwp.py <path-to-goldenballoon>

# 2. build and link inside the UWP toolchain
powershell -ExecutionPolicy Bypass -File tools\build-uwp.ps1 -Raiz <tree> -Toolchain <llvm-mingw>\bin `
     -Dawn <uwp-dep>\x64 -Sdl2 <SDL2 sources> -Enlazar

# 3. package and sign (your own tiles, your own certificate, your own ROM)
python tools\package_uwp.py --version 0.1.1.0 --exe <tree>\build-uwp\mdkr64.exe ...
```

Step by step, including the desktop builds that step 2 reads from and the console side:
**[`docs/INSTALL.md`](docs/INSTALL.md)** ([en español](docs/INSTALL.es.md)).

## What it had to solve

None of these is a console bug. All five are MinGW-vs-MSVC differences the desktop tree never had
to face, and **four of the five transfer to any other N64 decompilation** taken down this road.
The detail, with what the dump said in each case, is in
**[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)**.

| | Symptom | Cause |
|---|---|---|
| 1 | Racers invisible, text fine | `macros.h` disarmed **every** `__attribute__` in the tree, because clang targeting MSVC does not define `__GNUC__`. The casualty was the only `__attribute__((constructor))`: trigonometry returned 0 and the RNG was never seeded |
| 2 | 4750 compile errors | `-mno-ms-bitfields` cannot be used with the MSVC ABI — and removing it blindly grows the `Gfx` union from 8 bytes to 16 and desynchronises the whole display list. Two structures needed fixing; the layout dump found which |
| 3 | ~1300 undefined symbols from zstd | Visual Studio's `emmintrin.h` only *declares* the SSE2 intrinsics. Clang's headers have to come first |
| 4 | Launches, dies instantly, nothing on screen | `setvbuf(…, _IOLBF, 0)`. MinGW swallows the zero; UCRT fast-fails inside an App Container. A latent desktop bug the strict CRT exposes |
| 5 | Link fails on `sprintf` | UCRT emits an inline copy in every unit, which collides with the decomp's own definition. The one that has no callers anywhere |

And two things the console does that a PC does not: **B closed the game** (the system reads it as
back-navigation and closes the app unless you mark the event handled), and there is no keyboard,
so the FPS counter is drawn by the game and toggled with **R3**.

## How it was judged good

Not with a screenshot. The same deterministic stretch is run on the PC and on the console and the
simulation hashes are compared: **900 of 900 match** — the console simulates exactly what the PC
does.

And the recipe is judged separately from the port: applied to a clean `v1.7.0` checkout, it
reproduces all sixteen files the port touches, and building it gives **256 of 256 objects with an
identical `.text` section** against the tree that runs on the console. The executables differ by 13
bytes out of 5,829,120 — the link timestamp and the debug GUID. See [`CHANGELOG.md`](CHANGELOG.md).

## Credits and license

Port and tooling by **Recompilaciones**. Released under the [MIT License](LICENSE), matching the
license of [Golden Balloon](https://github.com/akratch/goldenballoon), the project this is a
derivative of.

The patch scripts and the code they write carry their comments in Spanish, which is where they
were written; the documentation is in both languages.

*Diddy Kong Racing* is © Nintendo / Rare. This project is not affiliated with them, with
Microsoft, or with the authors of Golden Balloon or of the decompilation it derives from, and it
distributes nothing that belongs to them. Exactly what is and is not included here — including
the 57 lines of upstream code it quotes, and where each one comes from — is accounted for in
[`NOTICE.md`](NOTICE.md). Rights holders can write to **jajdpmail@gmail.com**.
