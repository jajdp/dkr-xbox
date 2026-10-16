# How it works

*(Español: [HOW-IT-WORKS.es.md](HOW-IT-WORKS.es.md))*

Why this port is shaped the way it is, and what each patch is actually fixing. Read this if you
want to port another decompilation the same way: **four of the five hard parts are not specific to
this game.**

If you just want to build it, go to [`INSTALL.md`](INSTALL.md).

---

## 1. The method: translate the desktop build, don't maintain a second one

The obvious way to build a console port is to write a second CMake project. Don't. The upstream
moves fast — this port was written against `v1.7.0`, and the release before it was four weeks
old — and a hand-maintained file list falls behind in days.

What this port does instead:

1. Read `build.ninja` from the desktop configuration and take the exact list of objects that go
   into `mdkr64.exe`: its own, plus the ones from the static libraries built in the tree.
2. Read `compile_commands.json` and take the exact compile command CMake already emitted for
   each one.
3. Translate each command into the console's dialect and run it.

**A file the upstream adds appears on its own.** There is no list to maintain. The whole
translation is `tools/build_uwp.py`, and it is this:

| What changes | From | To | Why |
|---|---|---|---|
| Compiler | `gcc`/`g++` | `clang` | It is the one that can emit the MSVC ABI |
| Target | `x86_64-w64-windows-gnu` | `x86_64-pc-windows-msvc` | UWP requires the MSVC ABI and CRT |
| API family | (undefined) | `-DWINAPI_FAMILY=WINAPI_FAMILY_APP` | Hides the APIs an App Container cannot use |
| CRT | clang's default (static) | `-fms-runtime-lib=dll` | A store app uses the CRT as a DLL (`vcruntime140_app`) |
| WebGPU | wgpu-native | **Dawn** | wgpu-native has no UWP target at all ([`DEPENDENCIES.md`](DEPENDENCIES.md)) |
| SDL | SDL2 from MSYS2 | **SDL2 built for WinRT** | The WinRT backend is the one that hands over the `CoreWindow` |
| Forced header | — | `-include platform/uwp/uwp_compat.h` | The whole compatibility layer, in one file |
| Linker | MinGW `ld` | `ld.lld -flavor link /APPCONTAINER` | Under `vcvarsall.bat x64 store` |

**The desktop launcher is switched off.** `-DMDKR_APP=OFF` is a configuration the project already
supports — its wasm build uses it. It drops ImGui and `platform/app/`, returns `main()` to
`platform/main_pc.c` (which is exactly the entry the WinRT wrapper needs to wrap), and takes the
work from **320 objects down to 254**. On a console the game is launched from the system panel,
not from a window with a mouse pointer.

---

## 2. The entry point: WinRT without C++/CX

On a console there is no window to open. The system creates a `CoreWindow` and expects the
application to present itself as an `IFrameworkView` and hand over the thread. SDL already does
that dance — `SDL_WinRTRunApp` registers its own view, calls `CoreApplication::Run` and, once the
`CoreWindow` exists, invokes whatever function you gave it as if it were `main()`.

The problem is that **SDL's template is C++/CX** (`[Platform::MTAThread]`, `^`, `ref new`), which
only compiles with `cl.exe /ZW`. Clang does not speak C++/CX, and this whole port is clang.

It turns out the template does exactly two things, and both can be written in ordinary C++:

1. Initialise the apartment as multi-threaded, which `CoreApplication::Run` demands —
   `RoInitialize(RO_INIT_MULTITHREADED)`.
2. Call `SDL_WinRTRunApp`, which is C and already compiled inside `SDL2.lib`.

That is about 50 lines, and it means **no second toolchain**: the entire executable comes out of
clang + `ld.lld`. It is `src/uwp_entry.cpp`, which also handles three console-specific problems:

- **Where the ROM is.** `main_pc.c` resolves the default ROM as a *relative* path against the
  current directory, which is not something to rely on inside an App Container. The entry computes
  the install directory with `GetModuleFileNameW` — one of the very few location APIs still
  allowed in `WINAPI_FAMILY_APP` — and passes the path explicitly. If the activation already
  brought a path, that one wins.
- **Where the output goes.** There is no terminal, so everything the game says about itself was
  being lost — including Dawn's `[webgpu] device error` callback, which is what you need when a
  shader is rejected. `stdout` and `stderr` are redirected to `registro.txt` in `LocalState`.
  ⚠ Both streams are opened in append mode: with one in `"w"` and the other in `"a"` each keeps
  its own position over the same file and they overwrite each other.
- **How to steer it.** There is no command line either. Each line of `diagnostico.txt` in
  `LocalState` becomes either an argument or, if it is `NAME=VALUE`, an environment variable —
  `getenv()` always returns NULL in UWP because the process starts with no environment block, but
  the CRT keeps its own copy and `_putenv_s` writes into it. That is what puts the game's own
  instrumentation within reach on a console. Without the file, none of this exists, so **the
  binary you diagnose is exactly the binary you play**.

---

## 3. The five MSVC-ABI traps

None of these is a console problem. All five are MinGW-vs-MSVC differences that the desktop tree
never had to face — and **four of the five transfer to any other N64 decompilation** taken down
this road.

### 3.1 `__attribute__` silently disarmed — the one that cost the port

`game/include/PRinternal/macros.h` carries, for compilers that do not understand GCC attributes:

```c
#ifndef __GNUC__
#define __attribute__(x)
#endif
```

Clang **does** understand them — but when it targets `*-windows-msvc` it emulates MSVC's
predefined macros and **does not define `__GNUC__`**. The guard fired and disarmed every attribute
in the tree, with no warning and no link error.

What went with it was the project's **only `__attribute__((constructor))`**:
`mdkr64_fill_math_tables`, which fills `gSineTable` and `gArcTanTable` from the baked tables and
seeds the RNG. Two consequences:

- **All trigonometry returned 0.** Every rotation matrix degenerated, the 3D models collapsed and
  vanished — while 2D text, which does not rotate, kept drawing. On the console the intro showed
  the racers' names and no racers. It looked like a graphics driver bug.
- **The RNG was never seeded**, so the simulation diverged from the PC's: 2274 draws where the PC
  made 4273, and the state hash split at tick 89.

Fixed by naming `__clang__` alongside `__GNUC__` — one line, no effect on desktop.

> **Direct check:** the object must have a `.CRT$XCU` section. If it does not, the constructor is
> not there. This is worth checking on any decompilation ported this way, because nothing else
> tells you.

Patch: `tools/patch_attributes.py`.

### 3.2 `-mno-ms-bitfields` cannot be used with the MSVC ABI, and the game depended on it

Clang rejects the flag outright ("Itanium-compatible layout for the Microsoft C++ ABI is not yet
supported"): 4750 errors, one cause.

But dropping it blindly would have been worse. Dumping the record layouts with
`-fdump-record-layouts` under both packing rules showed that the `Gfx` union went from **8 bytes
to 16** — and half the game walks the display list in 8-byte steps. There would have been no title
screen, just garbage.

Of **26 structures** dumped, only **two** diverged (`Gpopmtx` and `Gsetcolor`), and by a single
rule: *MSVC opens a new word when a bitfield is followed by a field of a different size.* Fixed by
making the types match — the same trick `Gsetcolor.color` already carried for the sibling LP64
problem — and verified twice: the MSVC dump became identical to the GCC one, and the GCC dump
before and after the patch agrees on every offset, size and alignment.

Later, while chasing the drawing bug, the sweep was repeated over all **249 translation units**:
1051 game structures compared, 2 diverge — `dirent` (this port's own, expected) and
`TrackRenderDetails`, which holds `char *` pointers and is therefore host-shaped and consistent
within a build. Packing was ruled out with data, not with an opinion.

Patch: `tools/patch_display_list.py`.

### 3.3 Clang's headers have to come before Visual Studio's

Visual Studio ships its own `emmintrin.h`, which only **declares** the SSE2 intrinsics — its
compiler resolves them in the backend. Clang's **defines** them as `static inline`. If MSVC's
wins, clang emits real calls to `_mm_loadu_si128` and friends, and the link fails with about 1300
undefined references coming out of the zstd inside basisu.

`clang-cl` would fix this with `-imsvc`; the `clang` driver does not accept it, so the order is
explicit: `-isystem <resource-dir>/include` goes first, then whatever `INCLUDE` holds.

This also constrains `src/strings.h` — see §4.

In `tools/build_uwp.py`, not a patch: it is a compiler flag, not a change to the tree.

### 3.4 `setvbuf(stdout, NULL, _IOLBF, 0)` killed the app at startup

The package installed, appeared in the console's list with its icon, and died instantly on launch.
There is no `stderr` to read on an Xbox, so the diagnosis came from the Device Portal: enable
crash dumps, launch, pull the 99 MB `.dmp`, and let `cdb` say it:

```text
ExceptionCode: c0000409   Subcode: 0x5 FAST_FAIL_INVALID_ARG

SDL2!SDL_WinRTApp::Run          <- SDL already had the CoreWindow and called our main
  mdkr64+0x442dad
    mdkr64+0x11a5ed
      ucrtbase!setvbuf
        ucrtbase!invoke_watson
```

`setvbuf`'s contract requires a size between 2 and `INT_MAX` when the mode is `_IOLBF` or
`_IOFBF`. **Zero is outside it.** MinGW swallows it; UCRT counts it as an invalid parameter and,
inside an App Container, the default handler does not return — it fast-fails.

It is a **latent bug in the desktop port that only the strict CRT exposes**, which is worth
remembering for any other game taken this way.

> Since that cycle the UWP build carries `-g -gcodeview` and links with `/DEBUG /PDB`, so the next
> dump gives function names instead of `mdkr64+0x11a5ed`. The `.pdb` stays on the PC; it does not
> go in the package.

Patch: `tools/patch_crt.py`.

### 3.5 The decomp's own `sprintf` collides with UCRT's `stdio.h`

The game defines its own `sprintf`. Under MinGW it coexisted with the CRT's, because that one
lives in a library and the linker only pulls it in if nobody else defines it. UCRT does not work
that way: its `stdio.h` **emits an inline copy in every unit**, so the game's strong definition
collides head-on.

The obvious workaround — `_NO_CRT_STDIO_INLINE` plus `legacy_stdio_definitions.lib` — **does not
work**, for a measurable reason: that library is a single object, so pulling in `printf` drags
`sprintf` along and the collision returns.

The answer came from the code itself: that `sprintf` has **no caller anywhere in the tree** — the
three places that name it are comments about this very problem — and `objects.c` says so outright,
"the game's own sprintf() is the N64 implementation and is not usable for host diagnostics". The
spacing-codes path does not go through it either; it goes straight to `DKR_VSPRINTF`. So on UWP it
stays out of the binary and the CRT's wins.

Patch: `tools/patch_crt.py`.

---

## 4. The compatibility layer

Three headers and one rule: **the game's code is not touched**. The layer is forced into every
translation unit with `-include`, so it lives in one file that is easy to rebase when the upstream
moves.

| File | What it solves |
|---|---|
| `src/uwp_compat.h` | Six symbols the UWP CRT does not expose — `_getpid`, `clock_gettime`, `nanosleep`, `strtok_r`, `CreateFileW` → `CreateFile2` — plus the `#undef`s that `windows.h` forces (see below) |
| `src/dirent.h` | POSIX directory walking the MSVC CRT does not ship, on top of `FindFirstFileExW`, which **is** allowed in an App Container (`FindFirstFileA` is not) |
| `src/strings.h` | `strcasecmp` and `ffs` |

Two things in there are not obvious:

**`windows.h` in every unit breaks four identifiers.** Forcing the layer everywhere drags
`windows.h` into files that never included it, and that brings legacy macros which collide with
legitimate names: `windef.h` defines `near` and `far` (16-bit heritage), which breaks `gu_port.c`
where they are variable names in the projection matrices; `wingdi.h` defines `TRANSPARENT` and
`OPAQUE`, which break the `TextureRenderModes` enum. They are undefined one by one rather than
with `NOGDI`, which would take out things that are used.
⚠ And there is a knock-on: `windef.h` defines `FAR` as `far` and `NEAR` as `near`, so undefining
the lowercase ones leaves the uppercase expanding to a name that no longer exists — and
`combaseapi.h` uses them (`LPSTREAM FAR * ppstm`). They are redefined as empty, which is what they
are worth today.

**`ffs` uses `__builtin_ctz`, not `<intrin.h>`.** The obvious implementation is
`_BitScanForward`, and it was written that way first. Including `<intrin.h>` here is a trap: by
§3.3 clang's headers come first, so the `<intrin.h>` that gets in is clang's, which drags
`mmintrin.h` and defines `__m64` as a vector type — right after `windows.h` has already defined it
as a union. The clash breaks the whole unit. `__builtin_ctz` does the same job with no header at
all.

---

## 5. WebGPU on a CoreWindow

The renderer talks to WebGPU through the project's own compatibility seam,
`platform/fast3d/gfx_webgpu_compat.h`, which had two branches: the browser (emdawnwebgpu) and
wgpu-native. The console is neither:

- the **shape** of the API is Dawn's, like the browser branch, because emdawnwebgpu *is* Dawn
  compiled to wasm;
- the **behaviour** is native, like the wgpu-native branch: presentation is explicit and there is
  no JS event loop to yield to.

So the port adds a third branch rather than scattering `#ifdef`s through the renderer. Everything
in it was verified against the `webgpu.h` of *that* Dawn, not assumed.

⚠ **Dawn does accept a `CoreWindow`, but under the old chained-struct name**:
`WGPUSurfaceDescriptorFromWindowsCoreWindow`, not the `WGPUSurfaceSource*` naming the rest of that
block uses. Searching only for the new name leads to the false conclusion that Dawn has no UWP
support.

The one setting that is lost: `desiredMaximumFrameLatency`, which needs
`WGPUSurfaceConfigurationExtras`, a wgpu-native-only extension. It only affects how many frames
are in flight, not what is drawn. It used to be guarded by an `#ifndef __EMSCRIPTEN__` *inside*
`gfx_webgpu.c` — a dialect leak the seam's own header forbids — and the patch moves that decision
into the seam, where that same file says it belongs.

Patch: `tools/patch_webgpu.py`.

---

## 6. Two things the console does that a PC does not

**The B button closed the game.** On a console, B is not just a pad button: the system also
translates it to back-navigation (`SystemNavigationManager.BackRequested`). If the application
does not mark that event as *handled*, the system does its default thing — **close it**. SDL2 has
the handler registered, but only marks the event if asked, with
`SDL_HINT_WINRT_HANDLE_BACK_BUTTON`. Set with `OVERRIDE` priority, before `SDL_WinRTRunApp`.

This does **not** take the button away from the game: the pad press arrives by another route
(Windows.Gaming.Input → `SDL_GameController`), so B still brakes and goes back in menus. The only
thing it stops meaning is "close the application". Leaving the game stays where it belongs on a
console: the Xbox button.

**There is no keyboard, so the FPS counter is on R3.** The counter is drawn by the game itself, at
the two points it draws per frame — the race HUD and `menu_loop` — and toggled by clicking the
right stick. It lives in `enh_speedometer.c` rather than a new file because the UWP build takes
its translation units from the commands CMake already emitted: a new unit would mean regenerating
the project.

⚠ It counts **presentations** (`g_frameCounter`), not calls to the draw function. The latter would
report the game's tick rate — 30/s — and would keep saying 30 with smooth presentation on, which
is exactly what the counter exists to confirm or deny.

Patch: `tools/patch_fps_counter.py`.

---

## 7. What the port does not change: the game runs at 30, on purpose

Diddy Kong Racing updates every **two** video fields. That is the N64 game's own cadence, not a
limitation of the port: `fb_update()` counts how many 60 Hz fields passed per frame and returns it
as `updateRate`, and movement, physics and the race clock all scale by it.

Golden Balloon separates simulation from presentation deliberately — its own design note is titled
"Original gameplay with modern presentation" — and offers `Video.FrameLimit` and
`Video.MotionSmoothing`, which reconstruct intermediate images without advancing physics, input or
timers. None of that is this port's doing, and none of it is patched here.

⚠ On the console the `mdkr64.ini` is **not read**: `mdkr_user_video_config_path()` resolves it
only under `__EMSCRIPTEN__`. The way in is the `diagnostico.txt` hook described in §2, which turns
`NAME=VALUE` lines into environment variables:

```text
MDKR_PRESENT_RATE=60
MDKR_PRESENT_SMOOTHING=interpolate
```

⚠ And give it the **number**, not `display`. The console does not report the TV's refresh rate
(`platform_present_display_rate()` returns 0), so that policy ends up with no deadline and
presents as fast as the machine allows — the counter read 88-90 instead of 60. With an explicit
rate the log says `policy=capped rate=60` and the counter reads 60 flat.
