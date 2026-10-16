# Dependencias: de dónde sale cada pieza

*(English: [DEPENDENCIES.md](DEPENDENCIES.md))*

Este repositorio **no** trae ninguna de estas cosas. Son trabajo ajeno, publicado por otra gente, y
las consigues tú. Esta página dice exactamente cuál, de dónde, y por qué esa y no otra.

Las versiones de la columna derecha son con las que se construyó y se probó el port. Las más nuevas
probablemente valgan; si alguna no, es lo primero que hay que volver atrás.

| Qué | De dónde sale | Construido y probado con |
|---|---|---|
| **El proyecto del juego** | [akratch/goldenballoon](https://github.com/akratch/goldenballoon) | `v1.7.0` |
| **Tu ROM** | Tu propio volcado. Revisión **1.1**: en los sets habituales, la marcada «(Rev A)» | SHA-256 `7de1a8f…40ba8bcf` |
| **llvm-mingw** (clang + `ld.lld`) | [mstorsjo/llvm-mingw](https://github.com/mstorsjo/llvm-mingw/releases), la release `x86_64` de Windows | clang 22.1.8 |
| **Dawn para UWP** (`webgpu_dawn`, `libuwp`, `dxcompiler`, `dxil`) | [SternXD/uwp-dep](https://github.com/SternXD/uwp-dep), carpeta `x64` | commit `6ba4aad` (2026-06-20) |
| **SDL2 para WinRT** | [libsdl-org/SDL](https://github.com/libsdl-org/SDL/releases), rama `SDL2`, compilado por ti | 2.32.10 |
| **Visual Studio** | Microsoft. Hacen falta las herramientas de C++ de escritorio; la carga de trabajo de UWP **no** ([INSTALL.es.md](INSTALL.es.md) §1) | 2022 Community 17.14.37628.2 |
| **SDK de Windows 10/11** | Viene con Visual Studio. Hacen falta `makeappx.exe` y `signtool.exe` | 10.0.26100 |
| **MSYS2 UCRT64** | [msys2.org](https://www.msys2.org/) | cmake 4.4.3, ninja 1.13.2 |
| **Python 3** + Pillow | [python.org](https://www.python.org/) · `pip install pillow` | 3.13 |
| **PowerShell** | El que **ya trae Windows**. No hay nada que instalar | Windows PowerShell 5.1 (y 7.6, con idéntico resultado) |

## Por qué cada una, y no la alternativa obvia

### Por qué clang y `ld.lld`, y no MSVC

**El juego bloquea MSVC a propósito.** Su CMake se niega a configurar con `cl.exe`, y no es un
descuido: el código decompilado depende de comportamientos de la familia GCC que el *front end* de
MSVC no da. Así que el compilador tiene que ser clang.

Pero clang tiene que apuntar al **ABI de MSVC** (`--target=x86_64-pc-windows-msvc`), porque es el
único que una Xbox acepta dentro de un AppContainer. Esa combinación —el *front end* de clang, el
ABI de MSVC y el CRT «store»— es la que monta `tools/build_uwp.py`, y es el motivo de que hubiera
que arreglar cinco cosas antes de que nada compilara ([`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md)).

llvm-mingw es simplemente un clang + `ld.lld` ya empaquetado para Windows que se sabe que funciona
aquí. Cualquier clang 18 o posterior con `ld.lld` y `llvm-objdump` debería valer: la compilación
solo llama a esos cuatro ejecutables, y `--toolchain` apunta a la carpeta que los tenga.

### Por qué Dawn, y no wgpu-native

El renderizador del juego habla con WebGPU, y en escritorio eso es **wgpu-native**. No puede llegar
a la consola: wgpu-native solo publica binarios GNU/MinGW para Windows, y su objetivo de Rust para
UWP es *tier 3* — no hay nada contra lo que enlazar.

**Dawn sí puede**, y alguien ya lo compiló para UWP: `SternXD/uwp-dep`, que su propio README
describe como «a mini-depot repository to house dependencies required by various UWP
ports/projects». Las licencias de lo que distribuye están en su carpeta `lic/`.

Dawn es otro dialecto de la misma API, y por eso el port añade una tercera rama a la costura de
compatibilidad que el propio proyecto ya tenía, en vez de sembrar `#ifdef` por el renderizador: ver
`tools/patch_webgpu.py`.

`libuwp.dll` es de la que depende `webgpu_dawn.dll`; `dxcompiler.dll` y `dxil.dll` se cargan en
caliente para compilar los sombreadores. Las cuatro salen de la misma carpeta y las cuatro van
dentro del paquete.

### Por qué SDL2, y por qué hay que compilarlo

La consola no le entrega una ventana a la aplicación: crea una `CoreWindow` y espera un
`IFrameworkView`. SDL2 tiene un **backend WinRT** que hace exactamente ese baile, y **SDL3 no tiene
backend WinRT en absoluto**, así que toca SDL2 —aunque el port de escritorio use en otros sitios el
sucesor de SDL3—.

No hay ningún SDL2 para WinRT precompilado que descargar, así que lo compilas: las fuentes de SDL2
traen una solución de Visual Studio en `VisualC-WinRT/` justo para esto. Paso a paso, en
[`INSTALL.es.md`](INSTALL.es.md) §2.

### Por qué MSYS2 UCRT64, y no MINGW64

Porque es lo que usa el CI del propio juego, y el motivo está en su
`.github/workflows/release.yml`: los ejecutables de MINGW64 enlazan el `msvcrt.dll` antiguo, cuyo
`fopen` rechaza el flag `x` de C11 del que depende toda escritura atómica de ajustes del proyecto.
El proyecto publicó una vez una build así y no podía guardar ni una preferencia.

MSYS2 solo hace falta para las builds **de escritorio**, que son de las que este port lee sus
órdenes de compilación. La compilación UWP en sí se lanza desde PowerShell.

## Lo que pones tú, y es tuyo

| | |
|---|---|
| **La ROM** | Revisión 1.1. El empaquetador verifica su SHA-256 antes de copiarla, así que la revisión equivocada se detiene en tu PC y no en una consola donde no puedes leer el error |
| **Un certificado de firma** | Uno autofirmado vale. Su `CN` tiene que coincidir con el `Publisher` de `package/Package.appxmanifest` — [`INSTALL.es.md`](INSTALL.es.md) §3 |
| **Los mosaicos del paquete** | Nueve PNG, hechos con el arte que tú elijas — [`ASSETS.es.md`](ASSETS.es.md) |
| **Una Xbox en modo desarrollador** | Y el paquete de dependencias VCLibs, que la consola necesita tener instalado una vez |
