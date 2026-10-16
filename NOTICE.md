# Notice

*(Español: [NOTICE.es.md](NOTICE.es.md))*

## Not affiliated

This is an unofficial, noncommercial fan project. It is **not affiliated with, endorsed by or
connected to Nintendo, Rare, Microsoft** or any of their subsidiaries, nor to the authors of
[Golden Balloon](https://github.com/akratch/goldenballoon), the native port this builds on, nor
to the authors of the [Diddy Kong Racing decompilation](https://github.com/DavidSM64/Diddy-Kong-Racing)
that project derives from. *Diddy Kong Racing*, *Xbox* and all related names and marks are the
property of their respective owners, and are used here only to say what this works with.

Nothing here is for sale, and nothing here is monetized.

## What this repository does not distribute

No game ROM. No game code beyond the quoted anchors accounted for below. No built executable. No
`.msix` package. No save data. No textures, audio, music, models, fonts or sprites. No package
tiles either — the ones on the real console were made from the game's cover art, which is why
`package/Assets/` is empty and [`docs/ASSETS.md`](docs/ASSETS.md) asks you to supply your own.

It also distributes none of the third-party binaries the build needs: the LLVM toolchain, the
Dawn/WebGPU libraries and the SDL2 build all come from their own publishers, and
[`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) says where each one is and under what license.

**Nothing here produces a playable game on its own.** You need your own legally dumped copy of
the ROM and a working checkout of Golden Balloon, neither of which this repository provides or
can provide.

## What it does contain of other people's work

**Anchors quoted from the Golden Balloon tree: 57 lines in total.** Every patch here quotes the
text it searches for before writing, so that it fails safely instead of corrupting a tree it does
not recognise. That quoted text is the whole of what this repository reproduces, and it breaks
down like this:

| Where from | Lines | What they are |
|---|---|---|
| `platform/` — the port layer, which Golden Balloon licenses under the [MIT License](https://github.com/akratch/goldenballoon/blob/main/LICENSE) | 36 | Function bodies and macro blocks in the SDL, WebGPU and speedometer code |
| `game/` — the decompiled game code, which the upstream project cannot license and does not claim to | 21 | Four struct field declarations in `gbi.h`, one `#ifndef` line in `macros.h`, two call sites in `game_ui.c`, four `#include`/call lines in `menu.c`, and ten lines of the `sprintf` definition in `printf.c` |

The 21 lines from `game/` are declarations and call sites — the minimum text needed to locate
where each patch applies. They reproduce no game logic, no data and no assets. Golden Balloon is
itself a derivative of the community decompilation, and its own
[DISCLAIMER.md](https://github.com/akratch/goldenballoon/blob/main/DISCLAIMER.md) sets out that
project's position, which this one follows.

**Everything else here is first-party work**: 533 lines in `src/` (the WinRT entry point, the UWP
compatibility layer and two POSIX headers the MSVC CRT does not ship), 268 lines the patches
write into the tree, and all of `tools/`, `package/` and `docs/`. It is released under the
[MIT License](LICENSE), matching the upstream project's.

**`src/dirent.h` and `src/strings.h`** are minimal reimplementations written for this port, not
copies: they map the handful of POSIX symbols the game actually uses onto their Windows
equivalents. `dirent.h` covers directory walking; `strings.h` covers `strcasecmp` and `ffs`.

## Takedown and contact

If you hold rights in this material and want something here removed or changed, write to
**jajdpmail@gmail.com**, saying what you object to and in what capacity you are writing.

Requests from rights holders are honoured: the disputed part is removed, or the repository is
taken down, without argument, and you will get a reply confirming it. No notice or legal process
beyond that email is needed to reach the person who maintains this.
