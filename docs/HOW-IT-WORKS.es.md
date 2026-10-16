# Cómo funciona

Por qué el port es como es, y qué arregla de verdad cada parche. Léelo si quieres llevar otra
decompilación por el mismo camino: **cuatro de las cinco partes difíciles no son específicas de
este juego**.

*(English: [HOW-IT-WORKS.md](HOW-IT-WORKS.md))*

Si solo quieres construirlo, vete a [`INSTALL.es.md`](INSTALL.es.md).

---

## 1. El método: traducir la build de escritorio, no mantener otra

La forma obvia de construir un port de consola es escribir un segundo proyecto de CMake. No lo
hagas. El proyecto base se mueve rápido —este port se escribió contra la `v1.7.0`, y la versión
anterior tenía cuatro semanas— y una lista de archivos mantenida a mano se queda atrás en días.

Lo que hace este port en su lugar:

1. Leer `build.ninja` de la configuración de escritorio y tomar la lista exacta de objetos que
   entran en `mdkr64.exe`: los suyos, más los de las bibliotecas estáticas que se construyen en el
   árbol.
2. Leer `compile_commands.json` y tomar la orden de compilación exacta que CMake ya emitió para
   cada uno.
3. Traducir cada orden al dialecto de la consola y volver a ejecutarla.

**Un archivo que añada el proyecto base aparece solo.** No hay lista que mantener. Toda la
traducción es `tools/build_uwp.py`, y es esto:

| Qué cambia | De | A | Por qué |
|---|---|---|---|
| Compilador | `gcc`/`g++` | `clang` | Es el que sabe emitir el ABI de MSVC |
| Destino | `x86_64-w64-windows-gnu` | `x86_64-pc-windows-msvc` | UWP exige el ABI y el CRT de MSVC |
| Familia de API | (sin definir) | `-DWINAPI_FAMILY=WINAPI_FAMILY_APP` | Esconde las API que un AppContainer no puede usar |
| CRT | el de clang por omisión (estático) | `-fms-runtime-lib=dll` | Una app de la tienda usa el CRT en DLL (`vcruntime140_app`) |
| WebGPU | wgpu-native | **Dawn** | wgpu-native no tiene objetivo UWP ([`DEPENDENCIES.es.md`](DEPENDENCIES.es.md)) |
| SDL | SDL2 de MSYS2 | **SDL2 compilado para WinRT** | El backend WinRT es el que entrega la `CoreWindow` |
| Cabecera forzada | — | `-include platform/uwp/uwp_compat.h` | La capa de compatibilidad entera, en un archivo |
| Enlazador | `ld` de MinGW | `ld.lld -flavor link /APPCONTAINER` | Bajo `vcvarsall.bat x64 store` |

**El lanzador de escritorio se apaga.** `-DMDKR_APP=OFF` es una configuración que el propio
proyecto soporta: la usa su build de wasm. Quita ImGui y `platform/app/`, devuelve `main()` a
`platform/main_pc.c` —que es justamente el arranque que el envoltorio WinRT necesita envolver— y
baja el trabajo de **320 objetos a 254**. En una consola el juego se abre desde el panel del
sistema, no desde una ventana con puntero de ratón.

---

## 2. La entrada: WinRT sin C++/CX

En una consola no hay ventana que abrir. El sistema crea una `CoreWindow` y espera que la
aplicación se presente como un `IFrameworkView` y le ceda el hilo. SDL ya hace ese baile:
`SDL_WinRTRunApp` registra su propia vista, llama a `CoreApplication::Run` y, cuando la
`CoreWindow` ya existe, invoca la función que se le pase como si fuera `main()`.

El problema es que **la plantilla de SDL es C++/CX** (`[Platform::MTAThread]`, `^`, `ref new`), que
solo compila con `cl.exe /ZW`. Clang no habla C++/CX, y todo este port es clang.

Resulta que la plantilla hace exactamente dos cosas, y las dos se pueden escribir en C++ normal:

1. Inicializar el apartamento como multihilo, que es lo que exige `CoreApplication::Run`:
   `RoInitialize(RO_INIT_MULTITHREADED)`.
2. Llamar a `SDL_WinRTRunApp`, que es C y ya viene compilada dentro de `SDL2.lib`.

Son unas 50 líneas, y significa que **no hace falta una segunda cadena de herramientas**: el
ejecutable entero sale de clang + `ld.lld`. Es `src/uwp_entry.cpp`, que además resuelve tres
problemas propios de la consola:

- **Dónde está la ROM.** `main_pc.c` resuelve la ROM por omisión como ruta *relativa* contra el
  directorio actual, que no es algo con lo que convenga contar dentro de un AppContainer. La
  entrada calcula el directorio de instalación con `GetModuleFileNameW` —una de las poquísimas API
  de localización que siguen permitidas en `WINAPI_FAMILY_APP`— y pasa la ruta explícita. Si la
  activación ya trajo una ruta, manda esa.
- **Dónde va la salida.** No hay terminal, así que todo lo que el juego cuenta de sí mismo se
  perdía, incluido el callback `[webgpu] device error` de Dawn, que es lo que necesitas cuando
  rechaza un sombreador. `stdout` y `stderr` se redirigen a `registro.txt` en `LocalState`.
  ⚠ Los dos flujos se abren en modo «añadir»: con uno en `"w"` y otro en `"a"` cada uno lleva su
  propia posición sobre el mismo archivo y se pisan las escrituras.
- **Cómo conducirlo.** Tampoco hay línea de órdenes. Cada línea de `diagnostico.txt` en
  `LocalState` se convierte o en un argumento o, si es `NOMBRE=VALOR`, en una variable de entorno:
  `getenv()` siempre devuelve NULL en UWP porque el proceso arranca sin bloque de entorno, pero el
  CRT guarda su propia copia y `_putenv_s` escribe en ella. Eso es lo que pone la instrumentación
  del propio juego al alcance en una consola. Sin el archivo, nada de esto existe, así que **el
  binario que diagnosticas es exactamente el binario que juegas**.

---

## 3. Las cinco trampas del ABI de MSVC

Ninguna es un problema de la consola. Las cinco son diferencias entre MinGW y MSVC que el árbol de
escritorio nunca tuvo que afrontar, y **cuatro de las cinco sirven para cualquier otra
decompilación de N64** que se lleve por este camino.

### 3.1 `__attribute__` desarmado en silencio: la que costó el port

`game/include/PRinternal/macros.h` trae, para compiladores que no entienden los atributos de GCC:

```c
#ifndef __GNUC__
#define __attribute__(x)
#endif
```

Clang **sí** los entiende, pero cuando apunta a `*-windows-msvc` emula los predefinidos de MSVC y
**no define `__GNUC__`**. El guard se activaba y desarmaba todos los atributos del árbol, sin un
aviso y sin un error de enlace.

Lo que se fue con ellos fue el **único `__attribute__((constructor))`** del proyecto:
`mdkr64_fill_math_tables`, que rellena `gSineTable` y `gArcTanTable` desde las tablas horneadas y
fija la semilla del RNG. Dos consecuencias:

- **Toda la trigonometría devolvía 0.** Cada matriz de rotación degeneraba, los modelos 3D
  colapsaban y desaparecían, mientras el texto 2D, que no rota, seguía dibujándose. En la consola,
  la introducción enseñaba los nombres de los corredores y ningún corredor. Parecía un fallo del
  controlador gráfico.
- **El RNG nunca se sembraba**, así que la simulación divergía de la del PC: 2274 tiradas donde el
  PC daba 4273, y el hash de estado se separaba en el tick 89.

Arreglado nombrando `__clang__` junto a `__GNUC__`. Una línea, y en escritorio no cambia nada.

> **Comprobación directa:** el objeto tiene que tener una sección `.CRT$XCU`. Si no la tiene, el
> constructor no está. Vale la pena comprobarlo en cualquier decompilación llevada por esta vía,
> porque no hay ninguna otra cosa que te lo diga.

Parche: `tools/patch_attributes.py`.

### 3.2 `-mno-ms-bitfields` no se puede usar con el ABI de MSVC, y el juego dependía de él

Clang rechaza la bandera de plano («Itanium-compatible layout for the Microsoft C++ ABI is not yet
supported»): 4750 errores, una sola causa.

Pero quitarla a ciegas habría sido peor. El volcado de layouts con `-fdump-record-layouts` bajo las
dos reglas de empaquetado enseñó que la unión `Gfx` pasaba de **8 bytes a 16** — y medio juego
recorre el display list en saltos de 8. No habría habido pantalla de título, sino basura.

De **26 estructuras** volcadas, solo **dos** divergían (`Gpopmtx` y `Gsetcolor`), y por una sola
regla: *MSVC abre una palabra nueva cuando un campo de bits va seguido de otro de distinto tamaño*.
Se arregló igualando los tipos —el mismo truco que `Gsetcolor.color` ya llevaba para el problema
hermano de LP64— y se verificó dos veces: el volcado de MSVC quedó idéntico al de GCC, y el volcado
de GCC de antes y después del parche coincide en todos los desplazamientos, tamaños y alineaciones.

Más tarde, persiguiendo el fallo de dibujado, se repitió el barrido sobre las **249 unidades de
compilación**: 1051 estructuras del juego comparadas, 2 divergen — `dirent` (la propia del port,
esperada) y `TrackRenderDetails`, que lleva punteros `char *` y por tanto tiene la forma de la
máquina anfitriona y es consistente dentro de cada build. El empaquetado quedó descartado con
datos, no con una opinión.

Parche: `tools/patch_display_list.py`.

### 3.3 Las cabeceras de clang tienen que ir delante de las de Visual Studio

Visual Studio trae su propio `emmintrin.h`, que solo **declara** las intrínsecas SSE2 —su
compilador las resuelve en el backend—. El de clang las **define** como `static inline`. Si gana el
de MSVC, clang emite llamadas de verdad a `_mm_loadu_si128` y compañía, y el enlace se cae con unas
1300 referencias sin dueño que salen del zstd que trae basisu.

`clang-cl` lo arreglaría con `-imsvc`; el driver `clang` no lo acepta, así que el orden va
explícito: `-isystem <resource-dir>/include` primero, y después lo que traiga `INCLUDE`.

Esto además condiciona `src/strings.h` — ver §4.

Está en `tools/build_uwp.py`, no en un parche: es una bandera del compilador, no un cambio al árbol.

### 3.4 `setvbuf(stdout, NULL, _IOLBF, 0)` mataba la aplicación al arrancar

El paquete instalaba, aparecía en la lista de la consola con su icono y moría al instante al
lanzarlo. En una Xbox no hay `stderr` que leer, así que el diagnóstico salió del Device Portal:
activar volcados de fallo, lanzar, bajarse el `.dmp` de 99 MB y dejar que `cdb` lo dijera:

```text
ExceptionCode: c0000409   Subcode: 0x5 FAST_FAIL_INVALID_ARG

SDL2!SDL_WinRTApp::Run          <- SDL ya tenia el CoreWindow y llamo a nuestro main
  mdkr64+0x442dad
    mdkr64+0x11a5ed
      ucrtbase!setvbuf
        ucrtbase!invoke_watson
```

El contrato de `setvbuf` exige un tamaño entre 2 e `INT_MAX` cuando el modo es `_IOLBF` o `_IOFBF`.
**Cero está fuera.** MinGW se lo traga; UCRT lo cuenta como parámetro inválido y, dentro de un
AppContainer, el manejador por defecto no devuelve el control: hace *fast-fail*.

Es un **fallo latente del port de escritorio que solo el CRT estricto delata**, y conviene tenerlo
presente para cualquier otro juego llevado por aquí.

> Desde ese ciclo la build UWP lleva `-g -gcodeview` y enlaza con `/DEBUG /PDB`, para que el
> próximo volcado dé nombres de función en vez de `mdkr64+0x11a5ed`. El `.pdb` se queda en el PC;
> no entra al paquete.

Parche: `tools/patch_crt.py`.

### 3.5 El `sprintf` propio del decomp choca con el `stdio.h` de UCRT

El juego define su propio `sprintf`. Con MinGW convivía con el del CRT, porque aquel vive en una
biblioteca y el enlazador solo lo saca si nadie más lo define. UCRT no funciona así: su `stdio.h`
**emite una copia en línea en cada unidad**, de modo que la definición fuerte del juego choca de
frente.

El rodeo obvio —`_NO_CRT_STDIO_INLINE` más `legacy_stdio_definitions.lib`— **no sirve**, por una
razón medible: esa biblioteca es un solo objeto, así que sacar `printf` arrastra `sprintf` y el
choque vuelve.

La respuesta la daba el propio código: ese `sprintf` **no tiene ni un llamador en todo el árbol**
—los tres sitios que lo nombran son comentarios sobre este mismo asunto— y `objects.c` lo dice con
todas las letras: «the game's own sprintf() is the N64 implementation and is not usable for host
diagnostics». La ruta de *spacing codes* tampoco pasa por ahí: va directa a `DKR_VSPRINTF`. Así que
en UWP se queda fuera del binario y manda el del CRT.

Parche: `tools/patch_crt.py`.

---

## 4. La capa de compatibilidad

Tres cabeceras y una regla: **el código del juego no se toca**. La capa se mete en todas las
unidades de compilación con `-include`, así que vive en un solo archivo, fácil de rebasar cuando el
proyecto base se mueva.

| Archivo | Qué resuelve |
|---|---|
| `src/uwp_compat.h` | Seis símbolos que el CRT de UWP no expone —`_getpid`, `clock_gettime`, `nanosleep`, `strtok_r`, `CreateFileW` → `CreateFile2`— más los `#undef` que fuerza `windows.h` (abajo) |
| `src/dirent.h` | El recorrido de directorios POSIX que el CRT de MSVC no trae, sobre `FindFirstFileExW`, que **sí** está permitida en un AppContainer (`FindFirstFileA` no) |
| `src/strings.h` | `strcasecmp` y `ffs` |

Dos cosas de ahí dentro que no son obvias:

**`windows.h` en todas las unidades rompe cuatro identificadores.** Forzar la capa en todas partes
arrastra `windows.h` a archivos que nunca lo incluyeron, y eso trae macros heredadas que chocan con
nombres legítimos: `windef.h` define `near` y `far` (herencia de los 16 bits), que rompen
`gu_port.c`, donde son nombres de variable en las matrices de proyección; `wingdi.h` define
`TRANSPARENT` y `OPAQUE`, que rompen el enum `TextureRenderModes`. Se deshacen una a una y no con
`NOGDI`, que se llevaría por delante cosas que sí se usan.
⚠ Y hay un efecto colateral: `windef.h` define `FAR` como `far` y `NEAR` como `near`, así que
deshacer las minúsculas deja a las mayúsculas expandiéndose a un nombre que ya no existe — y
`combaseapi.h` las usa (`LPSTREAM FAR * ppstm`). Se redefinen vacías, que es lo que valen hoy.

**`ffs` usa `__builtin_ctz`, no `<intrin.h>`.** La implementación obvia es `_BitScanForward`, y así
estuvo escrita primero. Incluir `<intrin.h>` aquí es una trampa: por el §3.3 las cabeceras de clang
van delante, así que el `<intrin.h>` que entra es el de clang, que arrastra `mmintrin.h` y define
`__m64` como tipo vectorial, justo después de que `windows.h` ya lo haya definido como unión. El
choque rompe la unidad entera. `__builtin_ctz` hace lo mismo sin ninguna cabecera.

---

## 5. WebGPU sobre una CoreWindow

El renderizador habla con WebGPU a través de la costura de compatibilidad del propio proyecto,
`platform/fast3d/gfx_webgpu_compat.h`, que tenía dos ramas: el navegador (emdawnwebgpu) y
wgpu-native. La consola no es ninguna de las dos:

- la **forma** de la API es la de Dawn, como en la rama del navegador, porque emdawnwebgpu *es*
  Dawn compilado a wasm;
- el **comportamiento** es nativo, como en la rama de wgpu-native: la presentación es explícita y
  no hay bucle de eventos de JS al que ceder.

Así que el port añade una tercera rama en vez de sembrar `#ifdef` por el renderizador. Todo lo que
hay en ella está verificado contra el `webgpu.h` de *ese* Dawn, no supuesto.

⚠ **Dawn sí acepta una `CoreWindow`, pero con el nombre antiguo del encadenado**:
`WGPUSurfaceDescriptorFromWindowsCoreWindow`, no la nomenclatura `WGPUSurfaceSource*` que usa el
resto de ese bloque. Buscar solo la nueva lleva a concluir, en falso, que Dawn no soporta UWP.

El único ajuste que se pierde: `desiredMaximumFrameLatency`, que necesita
`WGPUSurfaceConfigurationExtras`, una extensión exclusiva de wgpu-native. Solo afecta a cuántos
cuadros van en vuelo, no a lo que se dibuja. Iba guardado con un `#ifndef __EMSCRIPTEN__` *dentro*
de `gfx_webgpu.c` —una fuga de dialecto que la propia cabecera de la costura prohíbe— y el parche
mueve esa decisión a la costura, que es donde ese mismo archivo dice que debe vivir.

Parche: `tools/patch_webgpu.py`.

---

## 6. Dos cosas que hace una consola y no hace un PC

**El botón B cerraba el juego.** En una consola, B no es solo un botón del mando: el sistema lo
traduce además a la navegación «atrás» (`SystemNavigationManager.BackRequested`). Si la aplicación
no marca ese evento como *atendido*, el sistema hace lo suyo por defecto: **cerrarla**. SDL2 trae
el manejador registrado, pero solo marca el evento si se le pide, con
`SDL_HINT_WINRT_HANDLE_BACK_BUTTON`. Se pone con prioridad `OVERRIDE`, antes de `SDL_WinRTRunApp`.

Esto **no** le quita el botón al juego: la pulsación del mando llega por otro camino
(Windows.Gaming.Input → `SDL_GameController`), así que B sigue frenando y retrocediendo en los
menús. Lo único que deja de significar es «cierra la aplicación». Salir del juego queda donde
corresponde en una consola: el botón Xbox.

**No hay teclado, así que el contador de FPS va en R3.** Lo dibuja el propio juego, en los dos
puntos que dibuja por cuadro —el HUD de carrera y `menu_loop`—, y se conmuta pulsando el stick
derecho. Vive en `enh_speedometer.c` y no en un archivo nuevo porque la build UWP toma sus unidades
de compilación de las órdenes que CMake ya emitió: una unidad nueva obligaría a regenerar el
proyecto.

⚠ Cuenta **presentaciones** (`g_frameCounter`), no llamadas a la función de dibujado. Lo segundo
daría la cadencia de ticks del juego —30/s— y seguiría diciendo 30 con la presentación suave
encendida, que es justo lo que el contador existe para confirmar o desmentir.

Parche: `tools/patch_fps_counter.py`.

---

## 7. Lo que el port no cambia: el juego va a 30 a propósito

Diddy Kong Racing actualiza cada **dos** campos de vídeo. Esa es la cadencia del propio juego de
N64, no una limitación del port: `fb_update()` cuenta cuántos campos de 60 Hz pasaron por cuadro y
lo devuelve como `updateRate`, y el movimiento, las físicas y el reloj de carrera escalan por él.

Golden Balloon separa simulación y presentación a propósito —su propia nota de diseño se titula
«Original gameplay with modern presentation»— y ofrece `Video.FrameLimit` y
`Video.MotionSmoothing`, que reconstruyen imágenes intermedias sin adelantar físicas, entrada ni
temporizadores. Nada de eso es obra de este port, y nada de eso se parchea aquí.

⚠ En la consola el `mdkr64.ini` **no se lee**: `mdkr_user_video_config_path()` lo resuelve solo bajo
`__EMSCRIPTEN__`. La vía es el gancho `diagnostico.txt` del §2, que convierte las líneas
`NOMBRE=VALOR` en variables de entorno:

```text
MDKR_PRESENT_RATE=60
MDKR_PRESENT_SMOOTHING=interpolate
```

⚠ Y hay que darle el **número**, no `display`. La consola no informa del refresco de la tele
(`platform_present_display_rate()` devuelve 0), así que esa política se queda sin *deadline* y
presenta tan rápido como la máquina da: el contador marcaba 88-90 en vez de 60. Con una tasa
explícita el registro dice `policy=capped rate=60` y el contador marca 60 clavado.
