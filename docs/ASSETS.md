# Package tiles — you supply your own

*(Español: [ASSETS.es.md](ASSETS.es.md))*

`package/Assets/` is empty on purpose. The tiles on the real console were made from *Diddy Kong
Racing*'s cover art, which belongs to Nintendo and Rare, so they are not distributed here
([`NOTICE.md`](../NOTICE.md)).

The packer stops with a clear message if any of the nine is missing, so you will not find out on
the console.

## What you draw: four images

Put these four in a folder of your own, with these exact names and sizes:

| File | Size | What it becomes |
|---|---|---|
| `xbox-sq1.png` | 150 × 150 | The square tile — the game's box in the library |
| `xbox-sq2.png` | 300 × 300 | The same at 2×. **This is the one actually shown most of the time** |
| `xbox-ss1.png` | 620 × 300 | The splash screen, shown while the game loads |
| `xbox-ss2.png` | 1240 × 600 | The same at 2× |

Then:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
python tools/make_tiles.py --origen <your folder> --salida <tiles folder>
```

That copies those four and derives the other five from `xbox-sq2.png` (LANCZOS), because the
manifest demands them and nobody wants to draw a 24-pixel icon by hand:

| Derived | Sizes | Why it exists |
|---|---|---|
| `Square44x44Logo` | 44, 88, 24 | The small icon in application lists |
| `StoreLogo` | 50, 100 | What `<Properties><Logo>` requires |

## Four things that are easy to get wrong

- **The names without a scale qualifier have to exist too.** The package is built without a
  `resources.pri`, and then `makeappx` looks for literally the name the manifest gives — not the
  `scale-200` variant. That is why there is both `Square150x150Logo.png` and
  `Square150x150Logo.scale-200.png`.

- **There is no wide tile, and that is deliberate.** `Wide310x150Logo` is not declared in the
  manifest because in Developer Mode the console never shows it. Declaring it would mean
  maintaining two more images nobody ever sees.

- **Put the motif in the middle, with margin.** On the console the square tile is drawn inside a
  317 × 317 frame; the splash sits on a plain background at about 9 % of a 1920 × 1080 screen.
  Making the art bigger does not make it more readable — centring it does.

- **Transparent background if the motif is a cut-out logo**, opaque if it is a boxed cover. The
  manifest sets `BackgroundColor="transparent"`, so whatever is transparent shows the console's
  theme colour through.

## The whole list, for reference

These are the nine files `package_uwp.py` expects to find. This is a list, not something to
type:

```text
Square150x150Logo.png                              150 x 150
Square150x150Logo.scale-200.png                    300 x 300
SplashScreen.png                                   620 x 300
SplashScreen.scale-200.png                        1240 x 600
Square44x44Logo.png                                 44 x 44
Square44x44Logo.scale-200.png                       88 x 88
Square44x44Logo.targetsize-24_altform-unplated.png  24 x 24
StoreLogo.png                                       50 x 50
StoreLogo.scale-200.png                            100 x 100
```
