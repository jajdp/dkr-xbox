# Diddy Kong Racing en Xbox — el port UWP

Cómo coger [Golden Balloon](https://github.com/akratch/goldenballoon), el port nativo de
*Diddy Kong Racing* (N64, 1997), y hacerlo correr **en una Xbox Series X en modo desarrollador**,
como un paquete UWP que construyes y firmas tú.

*(English: [README.md](README.md))*

No existía ningún port UWP de este juego, así que se escribió desde cero: no hay un segundo
proyecto de CMake ni un árbol duplicado.

Y no es una demostración que llega al título: **el juego se ha terminado en la consola** —el modo
aventura, la segunda vuelta en espejo y el modo de pistas—. Son todos los modos que tiene el juego,
jugados hasta el final con mando, así que es jugable de principio a fin.

## En qué consola se probó

**En una Xbox Series X**, en modo desarrollador. Las dos consolas en las que se construyó y se probó esto
son Series X, así que es el único hardware al que se refiere cualquier cosa que se afirme aquí.

**En una Series S no se ha probado nunca, ni una vez.** Es otra máquina: menos memoria disponible para un
juego y una GPU más floja. Puede que funcione en una, puede que vaya más despacio, o puede que no
arranque; nada de aquí se ha medido en ella. Si lo ejecutas en una Series S, lo que obtengas no es lo que
dice este README, y ninguna de las cifras de aquí es una promesa sobre esa consola.

## Qué es este repositorio

**Una receta y las herramientas que la aplican** a tu propia copia, en tu propia máquina:

| | |
|---|---|
| `src/` | La entrada WinRT y la capa de compatibilidad de UWP: 533 líneas, todas propias |
| `tools/` | Cinco parches, el constructor, el empaquetador y el verificador — [índice](tools/README.md) |
| `package/` | El manifiesto del paquete |
| `docs/` | Cómo construirlo, y por qué es como es |

## Qué **no** es

Aquí no hay **ninguna ROM, ningún material artístico del juego, ningún ejecutable compilado,
ningún paquete `.msix`**. Esto no produce un juego jugable por sí solo, y nada de lo que se puede
descargar aquí es un juego. Hacen falta tu propio volcado legítimo de la ROM y una copia de Golden
Balloon ya funcionando. Ver [`NOTICE.es.md`](NOTICE.es.md).

Los nueve mosaicos del paquete tampoco están: los del port real están hechos con la carátula del
juego. Pones los tuyos — [`docs/ASSETS.es.md`](docs/ASSETS.es.md) da las medidas exactas, y el
empaquetador se detiene con un mensaje claro si falta alguno.

## Qué lo hace sostenible

**Traduce la build de escritorio en vez de mantener otra.** La lista de objetos sale de
`build.ninja` y la orden de compilación de cada uno, de `compile_commands.json`; cada una se
traduce al dialecto de la consola y se vuelve a ejecutar. Un archivo que añada el proyecto base
entra solo — y eso importa, porque este port se escribió contra la `v1.7.0` y la versión anterior
tenía cuatro semanas.

## Qué hace falta tener antes

| | |
|---|---|
| El proyecto del juego | [akratch/goldenballoon](https://github.com/akratch/goldenballoon) `v1.7.0`, **compilando y corriendo en tu PC primero** |
| Tu propia ROM | Revisión **1.1**: en los sets habituales, la marcada «(Rev A)». La 1.0 se rechaza |
| Visual Studio | Con las herramientas de C++ de escritorio, más el SDK de Windows 10/11. La versión no está fijada y la carga de UWP no hace falta — [`docs/INSTALL.es.md`](docs/INSTALL.es.md) §1 |
| PowerShell | El que ya trae Windows: **no hace falta PowerShell 7**. Las órdenes llevan `-ExecutionPolicy Bypass` porque un Windows de fábrica no deja correr un `.ps1` sin eso |
| llvm-mingw, Dawn para UWP, SDL2 compilado para WinRT | De dónde sale cada uno, y por qué ese: [`docs/DEPENDENCIES.es.md`](docs/DEPENDENCIES.es.md) |
| Una Xbox en modo desarrollador | Y un certificado para firmar; uno autofirmado vale |

## Cómo va

Tres órdenes. El §0 de [`docs/INSTALL.es.md`](docs/INSTALL.es.md) explica la terminal con más
calma, y el resto de esa guía es la versión larga de estas tres líneas.

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
# 1. parchea tu copia (idempotente, todo o nada, no borra nada)
python tools\apply_uwp.py <ruta de goldenballoon>

# 2. compila y enlaza dentro de la cadena de UWP
powershell -ExecutionPolicy Bypass -File tools\build-uwp.ps1 -Raiz <árbol> -Toolchain <llvm-mingw>\bin `
     -Dawn <uwp-dep>\x64 -Sdl2 <fuentes de SDL2> -Enlazar

# 3. empaqueta y firma (tus mosaicos, tu certificado, tu ROM)
python tools\package_uwp.py --version 0.1.1.0 --exe <árbol>\build-uwp\mdkr64.exe ...
```

Paso a paso, con las builds de escritorio de las que lee el paso 2 y la parte de la consola:
**[`docs/INSTALL.es.md`](docs/INSTALL.es.md)** ([in English](docs/INSTALL.md)).

## Qué hubo que resolver

Ninguno de estos es un fallo de la consola. Los cinco son diferencias entre MinGW y MSVC que el
árbol de escritorio nunca tuvo que afrontar, y **cuatro de los cinco sirven para cualquier otra
decompilación de N64** que se lleve por esta vía. El detalle, con lo que dijo el volcado en cada
caso, está en **[`docs/HOW-IT-WORKS.es.md`](docs/HOW-IT-WORKS.es.md)**.

| | Síntoma | Causa |
|---|---|---|
| 1 | Los corredores invisibles, el texto bien | `macros.h` anulaba **todos** los `__attribute__` del árbol, porque clang apuntando a MSVC no define `__GNUC__`. La víctima fue el único `__attribute__((constructor))`: la trigonometría devolvía 0 y el RNG nunca se sembraba |
| 2 | 4750 errores de compilación | `-mno-ms-bitfields` es incompatible con el ABI de MSVC — y quitarlo a ciegas lleva la unión `Gfx` de 8 bytes a 16 y desincroniza el display list entero. Había que arreglar dos estructuras; el volcado de layouts dijo cuáles |
| 3 | ~1300 símbolos sin resolver desde zstd | El `emmintrin.h` de Visual Studio solo *declara* las intrínsecas SSE2. Las cabeceras de clang tienen que ir primero |
| 4 | Arranca, muere al instante, nada en pantalla | `setvbuf(…, _IOLBF, 0)`. MinGW se traga el cero; UCRT hace fast-fail dentro de un AppContainer. Un fallo latente del port de escritorio que solo el CRT estricto delata |
| 5 | El enlace falla por `sprintf` | UCRT emite una copia en línea en cada unidad, que choca con la definición propia del decomp. La que no tiene ni un llamador en todo el árbol |

Y dos cosas que hace una consola y no hace un PC: **B cerraba el juego** (el sistema lo lee como
navegación «atrás» y cierra la aplicación si no marcas el evento como atendido), y no hay teclado,
así que el contador de FPS lo dibuja el juego y se conmuta con **R3**.

## Cómo se dio por bueno

No con una captura. Se corre el mismo tramo determinista en el PC y en la consola y se comparan
los hashes de simulación: **900 de 900 coinciden** — la consola simula exactamente lo mismo que
el PC.

Y la receta se juzga aparte del port: aplicada a una copia limpia de la `v1.7.0`, reproduce los
dieciséis archivos que el port toca, y al compilarla da **256 de 256 objetos con la sección
`.text` idéntica** frente al árbol que corre en la consola. Los ejecutables difieren en 13 bytes
de 5.829.120 — la marca de tiempo del enlace y el GUID de depuración. Ver
[`CHANGELOG.md`](CHANGELOG.md).

## Créditos y licencia

Port y herramientas de **Recompilaciones**. Se publica bajo la [licencia MIT](LICENSE), la misma
de [Golden Balloon](https://github.com/akratch/goldenballoon), el proyecto del que esto es un
derivado.

Los scripts de parcheo y el código que escriben llevan sus comentarios en castellano, que es
donde se escribieron; la documentación va en los dos idiomas.

*Diddy Kong Racing* es © Nintendo / Rare. Este proyecto no está afiliado a ellos, ni a Microsoft,
ni a los autores de Golden Balloon o de la decompilación de la que deriva, y no distribuye nada
que les pertenezca. Qué hay y qué no hay aquí exactamente —incluidas las 57 líneas de código del
proyecto base que cita, y de dónde sale cada una— está detallado en
[`NOTICE.es.md`](NOTICE.es.md). Los titulares de derechos pueden escribir a **jajdpmail@gmail.com**.
