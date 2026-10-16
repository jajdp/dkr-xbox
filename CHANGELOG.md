# Changelog

All notable changes to this repository. Dates are `YYYY-MM-DD`.

The versions here are **the repository's**, not the package's. The package version is whatever you
pass to `package_uwp.py --version`, and it has to go up on every package you install, because the
console will not replace a package with one of the same version.

## [1.0.3] — 2026-10-13

### Added

- **What the console has to be before you start.** In Developer Mode, powered on, on the same
  network as your PC — and **with your profile signed in**, which is the one that costs an
  afternoon: with no user signed in, the console installs the package, lists it, and then
  launching it does nothing at all. None of this was in the guide; it was only in the project's
  own internal documentation. - **The browser warning on the way into the Device Portal.** The
  console's certificate is issued by the console itself, so every browser objects to it. The
  guide used to say "accept the certificate warning" and no more. That is not something you can
  act on if you have never seen the screen, so it now names the buttons — in Edge, Chrome and
  Firefox — and says the portal will then ask for the username and password set in Dev Home. -
  **That the console never asks for the certificate you signed with.** In Developer Mode it
  installs any signed package without caring who signed it: the **Add** screen has no field for
  it. Looking for that field sends people hunting for a problem that does not exist. The
  section says so, and gives the one command that exports the `.cer` out of the package, for
  the case where the portal ever did refuse a signature. - **How to remove it from the console,
  and the warning that your saves go with it.** They live inside the package's `LocalState`
  (`mdkr64\mdkr64\save`), and they are gone with it — so the section says where they are and to
  download them through the portal's **File explorer** first. It also says that removing it
  touches nothing on your PC, and that *updating* does not need an uninstall at all.

## [1.0.2] — 2026-10-13

### Added

- **How to run the game at 60 presented FPS, in the install guide.** It was only in
  `HOW-IT-WORKS` §7, which explains *why* the game simulates at 30 and what the options are — but
  somebody who has just installed it and wants 60 should not have to read the technical document
  for one of the first things they will want to change. §8 now gives the two lines, where the file
  goes, and how to check it worked. It also says plainly what it is **not**: the 60 FPS are an
  option of Golden Balloon itself, not a mod from this repository. What this port adds is the hook
  that lets you switch it on **on a console**, where the game's own settings file is never read.
- **The commands no longer need PowerShell 7, and say so.** Every example invoked `pwsh`, which is
  PowerShell 7 and does **not** ship with Windows — so on a machine without it the first command
  fails with "pwsh is not recognized", and nothing in the requirements warned about it. It turns
  out the scripts never needed it: all three run under the Windows PowerShell 5.1 that comes with
  Windows, and the executable that comes out is byte-identical (256 of 256 objects with the same
  `.text`). The examples now use `powershell`, and PowerShell is listed as a requirement with the
  version it was tested on.
- **And they carry `-ExecutionPolicy Bypass`, because without it they do not run at all on a stock
  Windows.** The default execution policy is `Restricted`, under which a `.ps1` will not even
  load: *"cannot be loaded because running scripts is disabled on this system"*. The flag lifts
  that for one run only, changes nothing on the machine and needs no administrator — all of which
  the guide now explains, rather than asking anyone to change their system policy.
- **Every command block now says where to type it.** The guides were written as if the reader
  already knew to open a terminal, which folder to be in, and that a block starting with `$` is
  PowerShell. None of that is obvious if this is not your trade. Each block now names its terminal
  and the folder it runs from, and blocks that are *output* rather than commands are marked as
  such, so there is no guessing about what you are supposed to type.
- **It is spelled out that administrator is not needed — and that using it breaks one step.** The
  certificate is created in the store of whichever user runs the command, so creating it in an
  elevated window puts it where `signtool`, running as you, will not find it.
- **A new §0 in the install guide: how to open the terminal.** Which one, how to find it from the
  Start menu, how to move to a folder with `cd`, what the backticks at the end of a long command
  mean, and how to tell whether a command worked.
- **`tools/README.es.md` and `package/Assets/README.es.md`.** The two in-folder READMEs were the
  last English-only documents that explain how to use the repository. `.gitignore` had to be told
  to let the second one through, since that folder only admits its README by name.
- **`HOW-IT-WORKS.es.md`, `DEPENDENCIES.es.md` and `ASSETS.es.md`, under `docs/`.** Only
  the README, the NOTICE and the INSTALL guide were bilingual; the three documents that explain
  *why* the port is shaped this way, where every dependency comes from, and what art you have to
  supply were English-only — so a reader who came in through `README.es.md` landed in English on
  the first click. The Spanish documents link to the Spanish ones throughout.

### Fixed

- One stray "Visual Studio 2022" left in the SDL2 step of both install guides. The year is not
  what matters there either, and SDL2's own solution retargets to whatever you have.

## [1.0.0] — 2026-10-13

First published version. The port itself was built and confirmed playable on 2026-09-14; this is
the recipe for it, extracted, cleaned of anything local and verified against a clean checkout.

### The port

- **The UWP layer** (`src/`, 533 lines): the WinRT entry point without C++/CX, the compatibility
  header forced into every unit, and minimal `dirent.h` and `strings.h` for the handful of POSIX
  symbols the MSVC CRT does not ship.
- **Five patches** (`tools/patch_*.py`) over the Golden Balloon tree, grouped by problem rather
  than by file:
  - `patch_display_list.py` — portable bitfield layout for `Gpopmtx` and `Gsetcolor`, so the
    `Gfx` union stays 8 bytes under both packing rules.
  - `patch_attributes.py` — `__attribute__` survives clang targeting MSVC. This is the one that
    made the racers visible.
  - `patch_crt.py` — the `setvbuf` that fast-failed at startup, and the decomp's `sprintf`
    colliding with UCRT.
  - `patch_webgpu.py` — WebGPU on a `CoreWindow`, and a third branch in the project's dialect
    seam for native Dawn.
  - `patch_fps_counter.py` — an on-screen FPS counter toggled with R3.
- **The build** (`tools/build_uwp.py`): reads the desktop build's own compile commands and
  translates them, so a file added upstream needs no change here.
- **Packaging** (`tools/package_uwp.py`, `tools/make_tiles.py`): verifies the ROM by SHA-256
  before copying it, assembles, signs, and refuses to run while the manifest still has its
  `CHANGE-ME` placeholders.
- **Verification** (`tools/verify_uwp.py`): checks the binary really is UWP before you find out
  on a console that cannot tell you why.

### Prepared for publication

- Every local path became a required argument. Nothing in here points at any particular machine.
- The signing certificate's thumbprint is a parameter, and the manifest's `Publisher` and `Name`
  are `CHANGE-ME`.
- The package tiles are not distributed (they were made from the game's cover art);
  `docs/ASSETS.md` gives the sizes and `make_tiles.py` builds the nine from four of your own.
- The object inventory, which used to be a hand-made `.json` kept beside the build, is now
  computed from `build.ninja` — a saved list goes stale the moment upstream adds a file.
- Scripts that only existed to edit the private project's documentation were left out.

### How it was verified

The recipe was run against a clean checkout, from GitHub, on a tree that had never been touched:

- **The tree it produces is the tree that runs.** Applying this repository to a fresh `v1.7.0`
  checkout reproduces all sixteen files the port touches. Ten are byte-identical; four differ only
  in line endings, which `.gitattributes` governs on the upstream side; two differ only in a
  comment, where a pointer to a private project was removed before publishing.
- **The code it produces is the code that runs.** Building both trees with these scripts gives
  **256 of 256 objects with an identical `.text` section**, and executables that differ by **13
  bytes out of 5,829,120** — the link timestamp and the debug GUID, which change on every link.
- **The whole chain runs end to end**, from `configure-desktop.sh` through to a signed 28 MB
  `.msix`, using nothing but this repository and the upstream project.

One real bug came out of that test and is fixed here: clang records the process's **current
directory** in the debug information, so building the same sources from two different folders
produced different objects. `build_uwp.py` now pins it with `-fdebug-compilation-dir`, which is
what makes "did it build the same thing?" a question you can actually answer.

What is **not** verified here: nothing in this round was installed on a console. The port itself
was confirmed playable on 2026-09-14, and the binary this recipe produces matches that one.

### Known limitations

- `legacy_stdio_definitions.lib` is still on the link line. It is a leftover of the abandoned
  `_NO_CRT_STDIO_INLINE` approach; the binary that was tested on the console linked with it, and
  removing it has not been measured.
- The manifest declares eight capabilities, of which realistically only `expandedResources` and
  `codeGeneration` are needed. Trimming the rest means building, installing and testing a new
  version, which has not been done.
- `EntryPoint="uwp.App"` is inherited from the template and names a class that does not exist;
  what actually runs is the `WinMain` in `src/uwp_entry.cpp`. The game starts with this value as
  it is, and changing it has not been tried.
