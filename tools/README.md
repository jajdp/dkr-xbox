# The tools, and the order they go in

*(Español: [README.es.md](README.es.md))*

Eleven files. You only ever invoke four of them directly, in this order:

```text
1. configure-desktop.sh    the two desktop builds, in MSYS2        (INSTALL §4)
2. apply_uwp.py            patch the tree                           (INSTALL §5)
3. build-uwp.ps1           compile and link for the console         (INSTALL §5)
4. package_uwp.py          pack and sign the .msix                  (INSTALL §6)
```

The rest are called by those, or are there for when something goes wrong.

## What each one is

| | |
|---|---|
| `configure-desktop.sh` | Configures and builds the two desktop configurations this port reads from. Runs inside **MSYS2 UCRT64**, not PowerShell. The long one |
| `apply_uwp.py` | **The entry point.** Copies the four files of `src/` into `platform/uwp/` and runs the five patches in order. `--list` shows the steps without touching anything |
| `parchear.py` | What the patches share: read, check, substitute, write. Not run on its own. Worth reading once — it is where "all or nothing" and "idempotent" are actually implemented |
| `patch_display_list.py` | Portable bitfield layout for `Gpopmtx` and `Gsetcolor` |
| `patch_attributes.py` | `__attribute__` survives clang targeting MSVC |
| `patch_crt.py` | The `setvbuf` that fast-fails at startup, and the decomp's `sprintf` |
| `patch_webgpu.py` | WebGPU on a `CoreWindow`, and the Dawn branch of the dialect seam |
| `patch_fps_counter.py` | The on-screen FPS counter, toggled with R3 |
| `build-uwp.ps1` | Loads Visual Studio's **store** environment and hands over to `build_uwp.py`. Use this, not the Python directly |
| `build_uwp.py` | The translation itself: reads the desktop build's compile commands, rewrites them for the console, compiles and links |
| `make_tiles.py` | Your four images → the nine tiles the manifest needs |
| `package_uwp.py` | Verifies the ROM, assembles the package, signs it |
| `verify_uwp.py` | Checks the binary really is UWP. Run it before packaging |

## Reading the patches

Each one opens with the symptom, the cause and why the fix is that one — that prose is the point
of them, and [`../docs/HOW-IT-WORKS.md`](../docs/HOW-IT-WORKS.md)
([en español](../docs/HOW-IT-WORKS.es.md)) is the same story told once, end to end.

Below the prose is `CAMBIOS`, a list of triples:

```python
('platform/main_pc.c',       # the file, relative to the tree root
 # busca:                    # the text the patch looks for
 ('...'),
 # queda:                    # the text that replaces it
 ('...')),
```

The text each patch writes is, character for character, what the tree that was built and tested
on the console has. That is why it is quoted literally rather than generated.

## Three rules they all keep

- **All or nothing.** Every substitution is computed in memory first, and nothing is written
  until all of them match. A patch that touches five files and trips on the fourth leaves none of
  them written.
- **Idempotent, with no injected marker.** "Already applied" is decided by asking whether the new
  text is already there, not by a sentinel comment — so what lands in the tree is exactly what the
  working port has.
- **Atomic writes, and the file's own line endings are kept.** Golden Balloon has files with CRLF
  and files with LF, and its `.gitattributes` governs them; changing them here would fill the
  game tree's `git status` with files no patch touched.

## A note on language

The scripts and the comments they write carry their prose in Spanish, which is where they were
written. The documentation is in both languages. Nothing in the code they produce depends on it.
