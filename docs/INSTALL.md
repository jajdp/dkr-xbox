# Build and install

*(Español: [INSTALL.es.md](INSTALL.es.md))*

Start to finish: from a clean checkout of Golden Balloon to the game running on an Xbox Series in
Developer Mode.

**How long each step takes**, measured on the machine this was tested on (a recent desktop; your
mileage will differ, and the first three are one-time setup):

| Step | Time |
|---|---|
| §1-3 Installing Visual Studio, MSYS2, building SDL2, making a certificate | the bulk of it, the first time only |
| §4 The desktop builds | **~3 min** of compiling, plus however long the dependency downloads take on your line |
| §5 Patching, then building and linking the console binary | seconds, then **~40 s** for 256 objects |
| §6 Tiles and packaging | seconds |
| §7 Installing on the console | ~10 s once the upload finishes |

So once the toolchain is in place, a full rebuild is a couple of minutes. The first run is the
expensive one.

Everything you need to fetch, and where it comes from, is in
[`DEPENDENCIES.md`](DEPENDENCIES.md). Why the port is shaped this way is in
[`HOW-IT-WORKS.md`](HOW-IT-WORKS.md).

> **What this repository cannot give you.** No ROM, no game code, no built executable. You need
> your own legally dumped ROM — **revision 1.1**, which in the usual sets is the one marked
> "(Rev A)" — and a working checkout of Golden Balloon. See [`../NOTICE.md`](../NOTICE.md).

---

## 0. Before you start: where the commands go

This guide is full of blocks like this one. **They are all commands you type yourself** into a
terminal window, and each one says above it which terminal. If you have never used one, this
section is everything you need; if you have, skip it.

### The two terminals in this guide

**PowerShell** is the ordinary Windows terminal, and almost everything goes there:

1. Press the **Windows** key.
2. Type `powershell`.
3. Press **Enter** on *Windows PowerShell*.

A blue or black window opens with a line ending in `>`. That is where you type the command and
press **Enter**.

**The MSYS2 (UCRT64) bash** is only used in §4, to build the desktop builds. It is a different
terminal with its own icon, installed along with MSYS2 (§1):

1. Press the **Windows** key.
2. Type `MSYS2 UCRT64` — those exact words: MSYS2 installs **several** similar terminals (MINGW64,
   CLANG64, MSYS) and only the **UCRT64** one works here.
3. Press **Enter**.

> ⚠ **Do not mix them.** A PowerShell command typed into the MSYS2 bash fails, and the other way
> round. Every block in this guide says which one it belongs to.

### Two things you will need in both

**Moving to a folder.** Almost every command is typed *from a particular folder* — usually this
repository's. You get there with `cd` followed by the path, in quotes if it has spaces:

```powershell
cd "C:\Users\your-name\Downloads\dkr-xbox"
```

In the MSYS2 bash, paths are written differently: `C:\dkr` is `/c/dkr`.

**A shortcut that saves mistakes:** open the folder in File Explorer, click the address bar, type
`powershell` over whatever is there and press **Enter**. PowerShell opens already in that folder.

### You do not need administrator — and it is better not to

Nothing in this guide needs "run as administrator". All of it was built and tested from an ordinary
account.

> ⚠ And in one step, being administrator actively **breaks** it: the certificate in §3 is created in
> the store of whichever user runs the command. Create it in an elevated window and it lands in the
> administrator's store, so when you package — which you will do as yourself — `signtool` cannot
> find it and fails without saying why.
>
> The only things that ask for administrator rights are the **installers** for Visual Studio and
> MSYS2, and those ask on their own with their own prompt.

### How to tell whether a command worked

The ones in this guide are talkative: they finish by saying what they did. When something goes
wrong they say that too, and §9 has a table of the likeliest messages and what they mean.

A command that prints nothing has usually worked. If you want to be sure, this answers `True` when
the previous command succeeded and `False` when it did not:

```powershell
$?
```

---

## 1. Prerequisites

| | |
|---|---|
| **MSYS2 UCRT64** | For the desktop builds. UCRT64, not MINGW64 — the reason is in [`DEPENDENCIES.md`](DEPENDENCIES.md) |
| **Visual Studio** | With the **C++ desktop tools** (`Microsoft.VisualStudio.Component.VC.Tools.x86.x64`). See "Which Visual Studio" below — the version is not pinned, and the UWP workload is *not* required |
| **Windows 10/11 SDK** | Comes with Visual Studio. Needs `makeappx.exe` and `signtool.exe` |
| **llvm-mingw** | clang + `ld.lld` + `llvm-objdump` + `llvm-readobj` |
| **SDL2 sources** | Branch `SDL2`. You build it in §2 |
| **Dawn for UWP** | `SternXD/uwp-dep`, folder `x64` |
| **Python 3** | With Pillow, for the tiles: `pip install pillow` |
| **PowerShell** | The one Windows ships with (Windows PowerShell 5.1) is enough: **you do not need to install PowerShell 7**. Tested with both, and the binary that comes out is identical |
| **An Xbox** | In Developer Mode, on the same network, with a profile signed in |

### Which Visual Studio

**The version is not pinned.** `tools/build-uwp.ps1` finds it with
`vswhere -latest -products *`, so it takes the newest installation that has the C++ tools. It
never asks for 2022.

What the recipe actually needs from Visual Studio is two things, and both are checkable:

- `vcvarsall.bat` has to accept the **`store`** argument;
- the **App Container CRT** has to be there, at `VC\Tools\MSVC\<version>\lib\x64\store\`.

Check both in one go:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder.

```powershell
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath
Test-Path (Join-Path $vs 'VC\Auxiliary\Build\vcvarsall.bat')
Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory |
    ForEach-Object { Test-Path (Join-Path $_.FullName 'lib\x64\store') }
```

Two `True`s and you are fine.

> **The UWP workload is not required.** That is measured, not assumed: on the machine this port
> was built and tested on, neither `Microsoft.VisualStudio.ComponentGroup.UWP.VC` nor
> `Microsoft.VisualStudio.Component.UWP.VC.v143` is installed, and the store CRT is present and
> all 256 objects compile. The C++ desktop tools bring it.

> ⚠ **Newer is not automatically better here.** Microsoft has been winding down UWP support for
> years. If some future release stops shipping `lib\x64\store`, or `vcvarsall.bat` stops taking
> `store`, this recipe does not work on it however new it is — the checks above are what tells
> you, and they take ten seconds.

**Built and tested with:** Visual Studio Community 2022 17.14.37628.2, MSVC 14.44.35207, Windows
SDK 10.0.26100. Anything older than VS 2022 has not been tried.

Clone the game, **outside any path with spaces**:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder: the command makes its own.

```powershell
git clone --branch v1.7.0 https://github.com/akratch/goldenballoon.git C:\dkr
```

> ⚠ **The path must have no spaces.** `windres.exe` invokes the preprocessor without quoting the
> path, so a tree under `…\Documents\My stuff\…` fails to compile `mdkr64.rc` — and only that
> one; the other 1154 objects build fine. `C:\dkr` is plenty.

---

### Why the PowerShell commands carry `-ExecutionPolicy Bypass`

Because without it they do not work on a freshly installed Windows. The **execution policy**
Windows ships with is `Restricted`, and under it a `.ps1` file will not even load:

```text
... cannot be loaded because running scripts is disabled on this system.
```

`-ExecutionPolicy Bypass` lifts that restriction **for that one run only**: it changes nothing on
the system, leaves nothing open afterwards, and does not need administrator rights. That is why
every command here carries it, and why you are not asked to change your machine's policy.

⚠ And it is why they say `powershell` and not `pwsh`: **`pwsh` is PowerShell 7**, which does not
come with Windows. If you have it, it works too — swap `powershell` for `pwsh` and leave the rest —
but nothing here needs it.

---

## 2. Build SDL2 for WinRT

There is no prebuilt to download. SDL2's sources ship a Visual Studio solution for exactly this.

1. Download the SDL2 sources (not SDL3 — [it has no WinRT backend](DEPENDENCIES.md)) and unpack
   them somewhere short, e.g. `C:\sdl2-uwp\SDL2-2.32.10`.
2. Open `VisualC-WinRT\SDL-UWP.sln` in Visual Studio, let it retarget if it asks.
3. Build **Release | x64**.

You should end up with:

```text
C:\sdl2-uwp\SDL2-2.32.10\VisualC-WinRT\x64\Release\SDL-UWP\SDL2.dll
                                                          \SDL2.lib
```

---

## 3. A signing certificate, and the manifest

The console will not install an unsigned package. It does **not** need to know who signed it —
in Developer Mode a self-signed certificate is enough, and the Device Portal's **Add** page does
not even have a field for one.

⚠ This is where not opening the window "as administrator" really matters: the certificate is
created in the store of whichever user runs the command, so an elevated one would put it in the
administrator's store, and `signtool`, running as you, would not find it.

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder.

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject 'CN=YOUR-NAME' `
     -KeyUsage DigitalSignature -FriendlyName 'YOUR-NAME UWP dev' `
     -CertStoreLocation 'Cert:\CurrentUser\My' `
     -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
$c.Thumbprint
```

What each part fixes:

| Part | What it sets |
|---|---|
| `-Subject 'CN=YOUR-NAME'` | The publisher name. **It has to match the manifest exactly** |
| `-KeyUsage DigitalSignature` | That the key can sign |
| `2.5.29.37={text}1.3.6.1.5.5.7.3.3` | Enhanced Key Usage: **code signing**, which app packages require |
| `2.5.29.19={text}` | Basic Constraints: an end-entity certificate, not one that issues others |
| `-CertStoreLocation` | Your personal store, which is where `signtool` looks |

Keep the thumbprint it prints: that is what you pass as `--certificado`.

**Then edit `package/Package.appxmanifest`** and replace the two `CHANGE-ME` values:

- `Publisher="CN=YOUR-NAME"` — identical to the certificate's subject. If they differ the console
  rejects the package; `package_uwp.py` checks this before packing and tells you.
- `Name="…"` — the package's internal name. Together with the publisher it forms the **family**,
  which is how the console recognises the game and what its saves hang off. Changing it later
  makes a different game as far as the console is concerned, with empty saves, and the old one
  stays installed separately. Choose once.
- `PublisherDisplayName` — free text, shown to people.

⚠ **Leave `Version="0.1.0.0"` alone.** `package_uwp.py` looks for that exact text to substitute
the real version. If you change it the substitution silently does not happen, and the `.msix` ends
up named for one version and containing another — and the console will not replace a package with
one of the same version.

Back it up while you are here; it lasts a year. In **the same PowerShell window**, because it
uses the `$c` variable the previous command created:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder.

```powershell
Export-PfxCertificate -Cert $c -FilePath '<backup>\signing.pfx' `
    -Password (Read-Host 'Password' -AsSecureString)
```

---

## 4. The desktop builds

This is the long one, and the only step that is **not** PowerShell. ⚠ Paths are written
Linux-style in that terminal: if the repository is at `C:\Users\your-name\dkr-xbox`, you get
there with `cd /c/Users/your-name/dkr-xbox`.

> **Where to type this:** in **the MSYS2 UCRT64 terminal** — press the **Windows** key, type
> `MSYS2 UCRT64` and press **Enter**; MSYS2 installs several similar ones and only that one
> works here — in an ordinary window, from this repository's folder.

```bash
bash tools/configure-desktop.sh /c/dkr
```

It configures and compiles the full build, then configures a second one without the desktop
launcher. The script explains why there are two; the short version is that the complete build is
where the dependencies get downloaded and where harfbuzz and SheenBidi are compiled, and the
launcher-less one is where the real object list for a console comes from.

The configure step **needs network**: the project downloads a pinned wgpu-native prebuilt and
verifies it by SHA-256.

When it finishes you should have:

```text
C:\dkr\build\compile_commands.json
C:\dkr\build-sin-lanzador\compile_commands.json
C:\dkr\build-sin-lanzador\build.ninja
```

> This is also the point where you find out whether the game builds at all on your machine. If it
> does not, that is an upstream problem, not a port problem — and nothing below will work until
> it does.

---

## 5. Patch the tree and build the UWP executable

**Patch** (idempotent; running it twice changes nothing). This repository's folder is the one
with `tools\` and `docs\` inside it:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
python tools\apply_uwp.py C:\dkr
```

It copies the four files of the UWP layer into `platform\uwp\` and applies five patches. Each one
checks the text it expects before writing and stops rather than half-applying, so if your tree is
not `v1.7.0` you will be told which anchor did not match. `--list` shows the steps without doing
anything.

> ⚠ **If you interrupt it, run it again.** It is idempotent: the patches already applied
> report "ya estaba aplicado" and it carries on from where it stopped. This matters more than
> it sounds, because **the port builds and links perfectly well with a patch missing** — the
> FPS counter is an addition, not a requirement — so a half-patched tree gives you a working
> game quietly missing a feature. Let the command finish, and read the five lines it prints.

**Build and link.** Replace what is between `<…>` with your own paths, and keep the backticks at
the end of each line exactly as they are: they are what lets one long command span several
lines:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
powershell -ExecutionPolicy Bypass -File tools\build-uwp.ps1 `
     -Raiz C:\dkr `
     -Toolchain <llvm-mingw>\bin `
     -Dawn <uwp-dep>\x64 `
     -Sdl2 C:\sdl2-uwp\SDL2-2.32.10 `
     -Enlazar
```

That loads Visual Studio's **store** environment and hands the work to `tools\build_uwp.py`.
Roughly 260 objects; a few minutes on a modern machine. It ends with:

```text
  ENLAZA. C:\dkr\build-uwp\mdkr64.exe  (5.5 MB)
```

**Check that it really is a UWP binary** before packaging — a desktop binary packages fine and
then fails to launch with no useful message:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
python tools\verify_uwp.py --exe C:\dkr\build-uwp\mdkr64.exe --toolchain <llvm-mingw>\bin
```

It must say `APPCONTAINER: yes` and import `api-ms-win-*` rather than `kernel32.dll`.

---

## 6. Tiles, and the package

**Your tiles** — four images, nine files. Sizes and the things that are easy to get wrong are in
[`ASSETS.md`](ASSETS.md):

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
python tools\make_tiles.py --origen <your 4 PNGs> --salida C:\dkr\tiles
```

**Pack and sign.** The version has to be **higher** than whatever is installed on the console:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
python tools\package_uwp.py --version 0.1.1.0 `
       --exe C:\dkr\build-uwp\mdkr64.exe `
       --rom "<your ROM>.z64" `
       --dawn-bin <uwp-dep>\x64\bin `
       --sdl2-bin C:\sdl2-uwp\SDL2-2.32.10\VisualC-WinRT\x64\Release\SDL-UWP `
       --assets C:\dkr\tiles `
       --salida C:\dkr\out `
       --certificado <your thumbprint>
```

It verifies the ROM's SHA-256 **before** copying anything, assembles the package contents, runs
`makeappx` and signs with `signtool`. Result: `DiddyKongRacing_0.1.1.0_x64.msix`, about 28 MB.

> **The ROM travels inside the package.** It is 12 MB, so it fits comfortably, and that removes a
> manual step and a failure mode — starting the game with no data and staring at a black screen.
> The revision is checked here, on your PC, because on a console you cannot read the error.

---

## 7. Install it on the console

You need the console's Device Portal address — Dev Home shows it. The username and password are
the ones you set in Dev Home.

The game declares a dependency on **Microsoft.VCLibs.140.00**, which the console needs installed.
Get `Microsoft.VCLibs.x64.14.00.appx` from the Windows SDK (under
`Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Retail\x64\`) or from
Microsoft's App Installer distribution.

### Before you touch anything: how the console has to be

- **In Developer Mode**, with Dev Home installed. If it is not, that is a separate process with
  Microsoft and this guide does not cover it. - **Powered on and with your profile signed in.**
  ⚠ With no user signed in the console **will not open applications**: the package installs,
  shows up in the list, and launching it does nothing. This is one of the costliest things to
  work out on your own. - **On the same network as your PC.** - **Its address**, which **Dev
  Home** shows you on the console itself. The Device Portal listens on port **11443** over
  HTTPS. - **Portal username and password**: the ones you set in **Dev Home → Remote Access
  Settings** when you turned remote access on.

**With a browser:**

1. Open `https://<console IP>:11443` in the browser on your PC.

   ⚠ The browser will warn that **the site's certificate is not trusted**. That is normal and not
   a problem: the certificate belongs to the console, which issues it itself. Go in anyway — in
   Edge and Chrome, **Advanced** → **Continue to … (unsafe)**; in Firefox, **Advanced** →
   **Accept the Risk and Continue**. It will then ask for the portal's username and password.
2. **Home → My games & apps → Add**.
3. Choose the `.msix` as the package, and the VCLibs `.appx` as a dependency.
4. **Start**.

**With the REST API**, if you prefer scripting it — the endpoint is
`POST /api/app/packagemanager/package`, multipart.
⚠ Two things that cost time there: the multipart **boundary must not be quoted** (a quoted
boundary gets a 500), and uploads above roughly 256 MB fail — not a problem at 28 MB.

⚠ **`Success` does not mean installed.** The portal repeats the previous operation's result. The
install is done when the game shows up in the package list — it took 8 seconds in testing. Check
the list rather than the return value.

⚠ **Same version does not replace.** A *higher* version installed over it upgrades and keeps
saves. Uninstalling first deletes them.

> **The console will not ask you for the certificate you signed with.** In Developer Mode it
> installs any signed package without needing to know the signer: the **Add** screen does not even
> have a field for it. The certificate was needed on your PC, to sign (§3), and that is where its
> job ends.
>
> If the portal ever did reject the signature, what you would register on the console is the
> **public half** of your certificate — a `.cer` file — which comes out of the package itself:
>
> ```powershell
> (Get-AuthenticodeSignature -LiteralPath "<your .msix>").SignerCertificate |
>     Export-Certificate -FilePath "$env:USERPROFILE\Desktop\signing.cer"
> ```

Then open it with the controller, from **My games & apps**.

---

### Removing it from the console

⚠ **Your saves go with it.** They live inside the package, in its `LocalState`, and disappear with
it. To keep them, download them first from the Device Portal's **File explorer**: they are under
`LocalState\mdkr64\mdkr64\save`.

To uninstall, in the Device Portal: **My games & apps**, find the game in the list, and **Remove**.
Nothing on your PC is touched: the `.msix`, the project and your ROM stay where they were.

Reinstalling afterwards starts from scratch, with empty saves. To **update** without losing them
there is no need to uninstall, as the warning above says: just install a package with a higher
version on top, which is the `--version` you pass to `package_uwp.py` (§6).

---

## 8. First run, and what to check

- **B brakes and goes back. It does not close the game.** To leave, press the Xbox button — that
  is deliberate ([`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) §6).
- **R3 (click the right stick)** shows and hides the FPS counter. On the console it starts on.
- The game runs its simulation at **30 updates per second**, because that is the N64 game's own
  cadence, not a limitation of this port. You can **present** 60: see below.

### Running it at 60 presented FPS

The game **simulates** at 30 updates per second and that does not change: it is the N64 game's own
cadence, and physics and the race clock depend on it. What can go up is how many frames are
**presented**, by reconstructing the ones in between. The result moves like 60 without advancing
physics, input or timers.

> **This is not a mod from this repository.** It is an option in Golden Balloon itself, whose
> design note is titled *"Original gameplay with modern presentation"*. What this port adds is a
> way to switch it on **on a console**, where the game's settings file is not read.

It is done with a text file. With the game installed and run at least once:

1. Open the console's Device Portal in a browser and go to the app's **File explorer**, inside
   `LocalState\mdkr64\mdkr64\`.
2. Upload a file there called **`diagnostico.txt`** with these two lines:

```text
MDKR_PRESENT_RATE=60
MDKR_PRESENT_SMOOTHING=interpolate
```

3. Close the game completely and open it again.

Press **R3** and the counter should read 60.

⚠ **Give it the number, not the word `display`.** The console does not report the TV's refresh
rate, so with `display` the policy ends up with no deadline and presents as fast as it can — in
testing it read 88-90 instead of 60. If your TV runs at 120, put `120`.

To be sure, look at `registro.txt` in that same folder: it has to say `policy=capped rate=60`.
Deleting `diagnostico.txt` puts everything back.

If anything misbehaves, the game's own log is in `LocalState\mdkr64\mdkr64\registro.txt`, which
you can download through the Device Portal's file browser. That file is the single most useful
thing on the console: the WebGPU adapter it picked, the ROM validation, and Dawn's
`[webgpu] device error` callback all go there.

---

## 9. When something goes wrong

| What you see | What it is |
|---|---|
| A patch stops with "el ancla aparece 0 veces" | Your tree is not `v1.7.0`, or it was already modified. The message names the file and the anchor. Nothing was written |
| `falta el entorno «store»` | `build_uwp.py` was run directly. Use `tools\build-uwp.ps1`, which loads it |
| ~1300 undefined symbols from zstd | Clang's headers lost to Visual Studio's. [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) §3.3 |
| `verify_uwp.py` says no `APPCONTAINER` | Linked without `/APPCONTAINER`, or with the desktop environment |
| It installs but "Failed to launch the application" | Almost always the CRT: a desktop binary, or the VCLibs dependency missing on the console. Run `verify_uwp.py` first |
| It launches and dies instantly, nothing on screen | Enable crash dumps in the Device Portal, launch, pull the `.dmp`. That is how §3.4 was found |
| The console shows the old version | The version did not go up, or the manifest template's `Version=` was edited (§3) |
| Models are invisible but text draws | `patch_attributes.py` did not apply. [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) §3.1 |
