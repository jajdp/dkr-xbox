# Dependencies — where each piece comes from

*(Español: [DEPENDENCIES.es.md](DEPENDENCIES.es.md))*

This repository ships **none** of these. They are other people's work, published by other people,
and you fetch them yourself. This page says exactly which one, from where, and why that one and
not another.

Versions in the right-hand column are what the port was built and tested with. Newer ones will
probably work; if one does not, that is the first thing to change back.

| What | Where it comes from | Built/tested with |
|---|---|---|
| **The game project** | [akratch/goldenballoon](https://github.com/akratch/goldenballoon) | `v1.7.0` |
| **Your ROM** | Your own dump. Revision **1.1** — in the usual sets, "(Rev A)" | SHA-256 `7de1a8f…40ba8bcf` |
| **llvm-mingw** (clang + `ld.lld`) | [mstorsjo/llvm-mingw](https://github.com/mstorsjo/llvm-mingw/releases) — the `x86_64` Windows release | clang 22.1.8 |
| **Dawn for UWP** (`webgpu_dawn`, `libuwp`, `dxcompiler`, `dxil`) | [SternXD/uwp-dep](https://github.com/SternXD/uwp-dep), folder `x64` | commit `6ba4aad` (2026-06-20) |
| **SDL2 for WinRT** | [libsdl-org/SDL](https://github.com/libsdl-org/SDL/releases), branch `SDL2`, built by you | 2.32.10 |
| **Visual Studio** | Microsoft. Needs the C++ desktop tools; the UWP workload is **not** required ([INSTALL.md](INSTALL.md) §1) | 2022 Community 17.14.37628.2 |
| **Windows 10/11 SDK** | Comes with Visual Studio. Needs `makeappx.exe` and `signtool.exe` | 10.0.26100 |
| **MSYS2 UCRT64** | [msys2.org](https://www.msys2.org/) | cmake 4.4.3, ninja 1.13.2 |
| **Python 3** + Pillow | [python.org](https://www.python.org/) · `pip install pillow` | 3.13 |
| **PowerShell** | The one Windows **already ships**. Nothing to install | Windows PowerShell 5.1 (and 7.6, with identical results) |

## Why each one, and not the obvious alternative

### Why clang and `ld.lld`, and not MSVC

**The game blocks MSVC on purpose.** Its CMake refuses to configure with `cl.exe`, and that is
not an oversight: the decompiled code depends on GCC-family behaviour that MSVC's front end does
not provide. So the compiler has to be clang.

But clang has to target the **MSVC ABI** (`--target=x86_64-pc-windows-msvc`), because that is the
only ABI an Xbox accepts inside an App Container. That combination — clang's front end, MSVC's
ABI, the store CRT — is what `tools/build_uwp.py` sets up, and it is why five separate things had
to be fixed before anything compiled ([`HOW-IT-WORKS.md`](HOW-IT-WORKS.md)).

llvm-mingw is simply a packaged clang + `ld.lld` for Windows that is known to work here. Any
clang 18+ with `ld.lld` and `llvm-objdump` should do; the build only ever calls those four
executables, and `--toolchain` points at whichever folder has them.

### Why Dawn, and not wgpu-native

The game's renderer talks to WebGPU, and on the desktop that is **wgpu-native**. It cannot come
to the console: wgpu-native only publishes GNU/MinGW prebuilts for Windows, and its Rust target
for UWP is tier 3 — there is nothing to link against.

**Dawn can**, and someone already built it for UWP: `SternXD/uwp-dep`, described by its own README
as "a mini-depot repository to house dependencies required by various UWP ports/projects". The
licenses of what it ships are in its `lic/` folder.

Dawn is a different dialect of the same API, which is why the port adds a third branch to the
project's own compatibility seam rather than scattering `#ifdef`s — see `tools/patch_webgpu.py`.

`libuwp.dll` is what `webgpu_dawn.dll` depends on; `dxcompiler.dll` and `dxil.dll` are loaded at
runtime to compile shaders. All four come from the same folder and all four go in the package.

### Why SDL2, and why you have to build it

The console does not hand the application a window: it creates a `CoreWindow` and expects an
`IFrameworkView`. SDL2 has a **WinRT backend** that does exactly that dance, and `SDL3 has no
WinRT backend at all` — so SDL2 it is, even though the desktop port uses SDL3's successor
elsewhere.

There is no prebuilt SDL2 for WinRT to download, so you build it: the SDL2 sources ship a Visual
Studio solution under `VisualC-WinRT/` for precisely this. Step by step in
[`INSTALL.md`](INSTALL.md) §2.

### Why MSYS2 UCRT64, and not MINGW64

Because that is what the game's own CI uses, and the reason is in its
`.github/workflows/release.yml`: MINGW64 executables link the legacy `msvcrt.dll`, whose `fopen`
rejects the C11 `x` flag that every atomic settings write in the project depends on. The project
once published a build like that and it could not save a single preference.

You only need MSYS2 for the **desktop** builds — the ones this port reads its compile commands
from. The UWP build itself runs from PowerShell.

## What you supply that is yours

| | |
|---|---|
| **The ROM** | Revision 1.1. The packer verifies its SHA-256 before copying it, so the wrong revision stops on your PC and not on a console where you cannot read the error |
| **A signing certificate** | A self-signed one is fine. Its `CN` has to match the `Publisher` in `package/Package.appxmanifest` — [`INSTALL.md`](INSTALL.md) §3 |
| **The package tiles** | Nine PNGs, made from art of your choosing — [`ASSETS.md`](ASSETS.md) |
| **An Xbox in Developer Mode** | And the VCLibs dependency package, which the console needs installed once |
