# Aviso

*(English: [NOTICE.md](NOTICE.md))*

## Sin afiliación

Este es un proyecto de aficionado, no oficial y sin ánimo de lucro. **No está afiliado a
Nintendo, a Rare ni a Microsoft**, ni a ninguna de sus filiales, ni lo respaldan; tampoco a los
autores de [Golden Balloon](https://github.com/akratch/goldenballoon), que es el port nativo
sobre el que se construye, ni a los de la
[decompilación de Diddy Kong Racing](https://github.com/DavidSM64/Diddy-Kong-Racing) de la que
aquel deriva. *Diddy Kong Racing*, *Xbox* y los demás nombres y marcas son de sus titulares, y
aquí se usan solo para decir con qué funciona esto.

Nada de esto está a la venta ni se monetiza de ninguna forma.

## Qué NO se distribuye aquí

Ninguna ROM. Ningún código del juego más allá de las anclas que se detallan abajo. Ningún
ejecutable compilado. Ningún paquete `.msix`. Ninguna partida guardada. Ninguna textura, audio,
música, modelo, fuente ni sprite. Tampoco los mosaicos del paquete: los del port real están
hechos con la carátula del juego, y por eso `package/Assets/` está vacía y
[`docs/ASSETS.es.md`](docs/ASSETS.es.md) te pide los tuyos.

Tampoco se distribuye ninguno de los binarios ajenos que hacen falta para compilar: la cadena de
LLVM, las bibliotecas de Dawn/WebGPU y la build de SDL2 salen de quienes las publican, y
[`docs/DEPENDENCIES.es.md`](docs/DEPENDENCIES.es.md) dice dónde está cada una y bajo qué licencia.

**Nada de esto produce un juego jugable por sí solo.** Hace falta tu propio volcado legítimo de
la ROM y una copia funcionando de Golden Balloon, y este repositorio no aporta ni puede aportar
ninguna de las dos cosas.

## Qué contiene de trabajo ajeno

**Anclas citadas del árbol de Golden Balloon: 57 líneas en total.** Cada parche cita el texto que
busca antes de escribir, para fallar del lado seguro en vez de estropear un árbol que no
reconoce. Ese texto citado es todo lo que este repositorio reproduce, y se reparte así:

| De dónde | Líneas | Qué son |
|---|---|---|
| `platform/` — la capa del port, que Golden Balloon publica bajo la [licencia MIT](https://github.com/akratch/goldenballoon/blob/main/LICENSE) | 36 | Cuerpos de función y bloques de macros del código de SDL, WebGPU y el velocímetro |
| `game/` — el código decompilado del juego, que el proyecto base no puede licenciar y no pretende licenciar | 21 | Cuatro declaraciones de campos en `gbi.h`, una línea de `#ifndef` en `macros.h`, dos puntos de llamada en `game_ui.c`, cuatro líneas de `#include` y de llamada en `menu.c`, y diez líneas de la definición de `sprintf` en `printf.c` |

Las 21 líneas de `game/` son declaraciones y puntos de llamada: el texto mínimo para localizar
dónde se aplica cada parche. No reproducen lógica del juego, ni datos, ni material artístico.
Golden Balloon es a su vez un derivado de la decompilación comunitaria, y su propio
[DISCLAIMER.md](https://github.com/akratch/goldenballoon/blob/main/DISCLAIMER.md) expone la
posición de ese proyecto, que este sigue.

**Todo lo demás es trabajo propio**: 533 líneas en `src/` (la entrada WinRT, la capa de
compatibilidad de UWP y dos cabeceras POSIX que el CRT de MSVC no trae), las 268 líneas que los
parches escriben en el árbol, y todo `tools/`, `package/` y `docs/`. Se publica bajo la
[licencia MIT](LICENSE), la misma del proyecto base.

**`src/dirent.h` y `src/strings.h`** son reimplementaciones mínimas escritas para este port, no
copias: mapean los pocos símbolos POSIX que el juego usa de verdad a sus equivalentes de Windows.
`dirent.h` cubre el recorrido de directorios; `strings.h`, `strcasecmp` y `ffs`.

## Retirada y contacto

Si tienes derechos sobre este material y quieres que algo se quite o se cambie, escribe a
**jajdpmail@gmail.com** diciendo a qué te opones y en calidad de qué escribes.

Las peticiones de los titulares de derechos se atienden: se retira la parte en disputa, o el
repositorio entero, sin discusión, y recibirás respuesta confirmándolo. No hace falta ningún
aviso ni procedimiento legal más allá de ese correo para llegar a quien mantiene esto.
