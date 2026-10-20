# Construir e instalar

*(English: [INSTALL.md](INSTALL.md))*

De principio a fin: de una copia limpia de Golden Balloon al juego corriendo en una Xbox Series X
en modo desarrollador.

**Lo que tarda cada paso**, medido en la máquina donde se probó (un sobremesa reciente; en la tuya
será otra cosa, y los tres primeros son preparación de una sola vez):

| Paso | Tiempo |
|---|---|
| §1-3 Instalar Visual Studio y MSYS2, compilar SDL2, crear el certificado | el grueso, y solo la primera vez |
| §4 Las builds de escritorio | **~3 min** de compilación, más lo que tarden las descargas en tu línea |
| §5 Parchear, y compilar y enlazar el binario de consola | segundos, y **~40 s** los 256 objetos |
| §6 Mosaicos y empaquetado | segundos |
| §7 Instalar en la consola | ~10 s una vez subido |

O sea que, con la cadena ya montada, rehacerlo entero son un par de minutos. La cara es la primera
vez.

Todo lo que hay que conseguir, y de dónde sale cada cosa, está en
[`DEPENDENCIES.es.md`](DEPENDENCIES.es.md). Por qué el port es como es, en
[`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md).

> **Lo que este repositorio no te puede dar.** Ni ROM, ni código del juego, ni ejecutable. Hacen
> falta tu propio volcado legítimo de la ROM —**revisión 1.1**, que en los sets habituales es la
> marcada «(Rev A)»— y una copia funcionando de Golden Balloon. Ver [`../NOTICE.es.md`](../NOTICE.es.md).

---

## 0. Antes de empezar: dónde se escriben las órdenes

Esta guía está llena de bloques como este. **Todos son órdenes que tecleas tú** en una ventana de
terminal, y cada uno dice arriba en cuál. Si nunca has usado una, aquí está todo lo que hace falta
saber; si ya sabes, sáltate esta sección.

### Las dos terminales de esta guía

**PowerShell** es la terminal normal de Windows, y es donde va casi todo:

1. Pulsa la tecla **Windows**.
2. Escribe `powershell`.
3. Pulsa **Enter** sobre *Windows PowerShell*.

Se abre una ventana azul o negra con una línea que acaba en `>`. Ahí escribes la orden y pulsas
**Enter**.

**El bash de MSYS2 (UCRT64)** solo se usa en el §4, para compilar las builds de escritorio. Es otra
terminal distinta, con su propio icono, que instalas junto con MSYS2 (§1):

1. Pulsa la tecla **Windows**.
2. Escribe `MSYS2 UCRT64` — con esas palabras exactas: MSYS2 instala **varias** terminales
   parecidas (MINGW64, CLANG64, MSYS) y aquí solo sirve la **UCRT64**.
3. Pulsa **Enter**.

> ⚠ **No las mezcles.** Una orden de PowerShell escrita en el bash de MSYS2 falla, y al revés.
> Cada bloque de esta guía dice en cuál va.

### Dos cosas que vas a necesitar en las dos

**Moverte a una carpeta.** Casi todas las órdenes se escriben *desde una carpeta concreta* —
normalmente la de este repositorio. Para ir a ella se usa `cd` seguido de la ruta, y la ruta entre
comillas si tiene espacios:

```powershell
cd "C:\Users\tu-usuario\Downloads\dkr-xbox"
```

En el bash de MSYS2 las rutas se escriben distinto: `C:\dkr` es `/c/dkr`.

**Un atajo que ahorra errores:** abre la carpeta en el Explorador de archivos, haz clic en la barra
de direcciones, escribe `powershell` encima de lo que ponga y pulsa **Enter**. Se abre PowerShell ya
situado en esa carpeta.

### No hace falta administrador — y es mejor no usarlo

Nada de esta guía necesita «ejecutar como administrador». Todo lo de aquí se construyó y se probó
con una cuenta normal.

> ⚠ Y en un paso concreto, ser administrador lo **estropea**: el certificado del §3 se crea en el
> almacén del usuario que ejecuta la orden. Si lo creas en una ventana elevada, acaba en el almacén
> del administrador, y al empaquetar —que sí harás como tú— `signtool` no lo encuentra y falla sin
> decir por qué.
>
> Lo único que pide permisos de administrador son los **instaladores** de Visual Studio y de MSYS2,
> y eso lo piden ellos solos con su propia ventana.

### Cómo saber si una orden funcionó

Las de esta guía son habladoras: terminan diciendo qué hicieron. Si algo va mal, lo dicen también,
y el §9 tiene una tabla con los mensajes más probables y qué significan.

Una orden que no imprime nada suele haber funcionado. Y si quieres confirmarlo, esto responde `True`
cuando la anterior terminó bien y `False` cuando no:

```powershell
$?
```

---

## 1. Lo que hace falta tener

| | |
|---|---|
| **MSYS2 UCRT64** | Para las builds de escritorio. UCRT64 y no MINGW64: el motivo está en [`DEPENDENCIES.es.md`](DEPENDENCIES.es.md) |
| **Visual Studio** | Con las **herramientas de C++ de escritorio** (`Microsoft.VisualStudio.Component.VC.Tools.x86.x64`). Ver «Qué Visual Studio» más abajo: la versión no está fijada, y la carga de trabajo de UWP *no* hace falta |
| **SDK de Windows 10/11** | Viene con Visual Studio. Hacen falta `makeappx.exe` y `signtool.exe` |
| **llvm-mingw** | clang + `ld.lld` + `llvm-objdump` + `llvm-readobj` |
| **Fuentes de SDL2** | Rama `SDL2`. Se compila en el §2 |
| **Dawn para UWP** | `SternXD/uwp-dep`, carpeta `x64` |
| **Python 3** | Con Pillow, para los mosaicos: `pip install pillow` |
| **PowerShell** | El que trae Windows (Windows PowerShell 5.1) basta: **no hace falta instalar PowerShell 7**. Probado con las dos, y el binario que sale es idéntico |
| **Una Xbox** | En modo desarrollador, en la misma red y con un perfil iniciado |

### Qué Visual Studio

**La versión no está fijada.** `tools/build-uwp.ps1` lo busca con
`vswhere -latest -products *`, así que coge la instalación más reciente que tenga las herramientas
de C++. Nunca pregunta por la 2022.

Lo que la receta necesita de Visual Studio son dos cosas, y las dos se pueden comprobar:

- que `vcvarsall.bat` acepte el argumento **`store`**;
- que esté el **CRT para App Container**, en `VC\Tools\MSVC\<versión>\lib\x64\store\`.

Las dos de una vez:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde cualquier carpeta.

```powershell
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath
Test-Path (Join-Path $vs 'VC\Auxiliary\Build\vcvarsall.bat')
Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory |
    ForEach-Object { Test-Path (Join-Path $_.FullName 'lib\x64\store') }
```

Dos `True` y vas bien.

> **La carga de trabajo de UWP no hace falta.** Esto está medido, no supuesto: en la máquina donde
> se construyó y se probó el port no están instalados ni
> `Microsoft.VisualStudio.ComponentGroup.UWP.VC` ni
> `Microsoft.VisualStudio.Component.UWP.VC.v143`, y el CRT «store» está igualmente y los 256
> objetos compilan. Lo traen las herramientas de C++ de escritorio.

> ⚠ **Más nueva no es automáticamente mejor aquí.** Microsoft lleva años reduciendo el soporte de
> UWP. Si alguna versión futura deja de traer `lib\x64\store`, o `vcvarsall.bat` deja de aceptar
> `store`, esta receta no funciona en ella por muy nueva que sea: las comprobaciones de arriba son
> las que lo dicen, y son diez segundos.

**Construido y probado con:** Visual Studio Community 2022 17.14.37628.2, MSVC 14.44.35207, SDK de
Windows 10.0.26100. Nada anterior a VS 2022 se ha probado.

Clona el juego **fuera de cualquier ruta con espacios**:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde cualquier carpeta: la orden crea la suya.

```powershell
git clone --branch v1.7.0 https://github.com/akratch/goldenballoon.git C:\dkr
```

> ⚠ **La ruta no puede llevar espacios.** `windres.exe` invoca al preprocesador sin entrecomillar
> la ruta, así que un árbol bajo `…\Documentos\Mis cosas\…` falla al compilar `mdkr64.rc` — y solo
> ese: los otros 1154 objetos compilan bien. `C:\dkr` sobra.

---

### Por qué las órdenes de PowerShell llevan `-ExecutionPolicy Bypass`

Porque sin eso no funcionan en un Windows recién instalado. La **política de ejecución** que trae
Windows por defecto es `Restricted`, y con ella un archivo `.ps1` ni siquiera se carga:

```text
... cannot be loaded because running scripts is disabled on this system.
```

`-ExecutionPolicy Bypass` levanta esa restricción **solo para esa ejecución**: no cambia nada del
sistema, no deja nada abierto después, y no hace falta ser administrador para usarlo. Por eso las
órdenes de esta guía lo llevan siempre, y por eso no te pedimos que cambies la política de tu
equipo.

⚠ Y por eso ponen `powershell` y no `pwsh`: **`pwsh` es PowerShell 7**, que no viene con Windows.
Si lo tienes, también sirve —cambia `powershell` por `pwsh` y lo demás igual—, pero nada de aquí
lo necesita.

---

## 2. Compilar SDL2 para WinRT

No hay nada precompilado que descargar. Las fuentes de SDL2 traen una solución de Visual Studio
justo para esto.

1. Descarga las fuentes de SDL2 (no SDL3: [no tiene backend WinRT](DEPENDENCIES.es.md)) y
   descomprímelas en una ruta corta, p. ej. `C:\sdl2-uwp\SDL2-2.32.10`.
2. Abre `VisualC-WinRT\SDL-UWP.sln` en Visual Studio y deja que actualice el proyecto si lo
   pide.
3. Compila en **Release | x64**.

Tiene que quedarte:

```text
C:\sdl2-uwp\SDL2-2.32.10\VisualC-WinRT\x64\Release\SDL-UWP\SDL2.dll
                                                          \SDL2.lib
```

---

## 3. Un certificado de firma, y el manifiesto

La consola no instala un paquete sin firmar. **No** necesita saber quién lo firmó: en modo
desarrollador basta con un autofirmado, y la pantalla **Add** del Device Portal ni siquiera tiene
casilla para el certificado.

⚠ Aquí importa de verdad lo de **no** abrir la ventana «como administrador»: el certificado se
crea en el almacén del usuario que ejecuta la orden, así que elevado acabaría en el del
administrador y después `signtool`, corriendo como tú, no lo encontraría.

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde cualquier carpeta.

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject 'CN=TU-NOMBRE' `
     -KeyUsage DigitalSignature -FriendlyName 'TU-NOMBRE UWP dev' `
     -CertStoreLocation 'Cert:\CurrentUser\My' `
     -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
$c.Thumbprint
```

Qué fija cada parte:

| Parte | Qué fija |
|---|---|
| `-Subject 'CN=TU-NOMBRE'` | El nombre del editor. **Tiene que coincidir exactamente con el manifiesto** |
| `-KeyUsage DigitalSignature` | Que la clave sirva para firmar |
| `2.5.29.37={text}1.3.6.1.5.5.7.3.3` | El uso declarado: **firma de código**, el que piden los paquetes de aplicación |
| `2.5.29.19={text}` | Que es un certificado final, no una entidad que emite otros |
| `-CertStoreLocation` | Tu almacén personal, que es donde lo busca `signtool` |

Guarda la huella que imprime: es lo que se pasa en `--certificado`.

**Después edita `package/Package.appxmanifest`** y cambia los `CHANGE-ME`:

- `Publisher="CN=TU-NOMBRE"`, idéntico al sujeto del certificado. Si no coinciden, la consola
  rechaza el paquete; `package_uwp.py` lo comprueba antes de empaquetar y te lo dice.
- `Name="…"`, el nombre interno del paquete. Con el editor forma la **familia**, que es como la
  consola reconoce al juego y de la que cuelgan sus partidas. Cambiarlo más adelante crea otro
  juego a ojos de la consola, con las partidas en blanco, y el viejo se queda instalado aparte.
  Elígelo una vez.
- `PublisherDisplayName`, texto libre: es el que ve la gente.

⚠ **No toques `Version="0.1.0.0"`.** `package_uwp.py` busca ese texto exacto para sustituirlo por
la versión de verdad. Si lo cambias, la sustitución no ocurre y **no avisa**: el `.msix` sale
nombrado con una versión y con otra dentro, y la consola no reemplaza un paquete por otro de la
misma versión.

Ya que estás, sácale el respaldo; dura un año. En **la misma ventana de PowerShell**, porque
usa la variable `$c` que creó la orden anterior:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde cualquier carpeta.

```powershell
Export-PfxCertificate -Cert $c -FilePath '<respaldo>\firma.pfx' `
    -Password (Read-Host 'Contraseña' -AsSecureString)
```

---

## 4. Las builds de escritorio

Esta es la larga, y la única que **no** va en PowerShell. ⚠ En esa terminal las rutas se
escriben al estilo de Linux: si el repositorio está en `C:\Users\tu-usuario\dkr-xbox`, para ir
a él se escribe `cd /c/Users/tu-usuario/dkr-xbox`.

> **Dónde se escribe:** en **la terminal MSYS2 UCRT64** —pulsa la tecla **Windows**, escribe
> `MSYS2 UCRT64` y pulsa **Enter**; MSYS2 instala varias parecidas y aquí solo sirve esa—, en
> una ventana normal, desde la carpeta de este repositorio.

```bash
bash tools/configure-desktop.sh /c/dkr
```

Configura y compila la build completa, y después configura una segunda sin el lanzador de
escritorio. El script explica por qué son dos; en corto: la completa es donde se descargan las
dependencias y donde se compilan harfbuzz y SheenBidi, y la de sin lanzador es de donde sale la
lista de objetos que de verdad quiere una consola.

El configure **necesita red**: el proyecto descarga un prebuilt fijado de wgpu-native y lo
verifica por SHA-256.

Al terminar tienes que tener:

```text
C:\dkr\build\compile_commands.json
C:\dkr\build-sin-lanzador\compile_commands.json
C:\dkr\build-sin-lanzador\build.ninja
```

> Este es también el punto donde descubres si el juego compila siquiera en tu máquina. Si no
> compila, el problema es del proyecto base y no del port, y nada de lo de abajo va a funcionar
> hasta que compile.

---

## 5. Parchear el árbol y construir el ejecutable UWP

**Parchear** (idempotente: pasarlo dos veces no cambia nada). La carpeta de este repositorio es
la que tiene dentro `tools\` y `docs\`:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
python tools\apply_uwp.py C:\dkr
```

Copia los cuatro archivos de la capa UWP a `platform\uwp\` y aplica cinco parches. Cada uno
comprueba el texto que espera antes de escribir y se detiene en vez de quedarse a medias, así que
si tu árbol no es el `v1.7.0` te dirá qué ancla no cuadró. Con `--list` enseña los pasos sin tocar
nada.

> ⚠ **Si lo interrumpes, vuelve a lanzarlo.** Es idempotente: los parches ya aplicados
> dicen «ya estaba aplicado» y sigue por donde se quedó. Esto importa más de lo que parece,
> porque **el port compila y enlaza igual de bien con un parche de menos** —el contador de FPS
> es un añadido, no un requisito—, así que un árbol a medio parchear te da un juego que
> funciona y al que le falta algo sin decírtelo. Deja que el comando termine y lee las cinco
> líneas que imprime.

**Compilar y enlazar.** Sustituye lo que va entre `<…>` por tus rutas, y fíjate en las comillas
invertidas del final de cada línea: son las que dejan partir una orden larga en varias, así que
cópialas tal cual:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
powershell -ExecutionPolicy Bypass -File tools\build-uwp.ps1 `
     -Raiz C:\dkr `
     -Toolchain <llvm-mingw>\bin `
     -Dawn <uwp-dep>\x64 `
     -Sdl2 C:\sdl2-uwp\SDL2-2.32.10 `
     -Enlazar
```

Eso carga el entorno **store** de Visual Studio y le pasa el trabajo a `tools\build_uwp.py`. Son
unos 260 objetos: unos minutos en una máquina moderna. Termina con:

```text
  ENLAZA. C:\dkr\build-uwp\mdkr64.exe  (5.5 MB)
```

**Comprueba que es UWP de verdad** antes de empaquetar; un binario de escritorio se empaqueta sin
protestar y luego no arranca, sin ningún mensaje útil:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
python tools\verify_uwp.py --exe C:\dkr\build-uwp\mdkr64.exe --toolchain <llvm-mingw>\bin
```

Tiene que decir `APPCONTAINER: sí` e importar `api-ms-win-*` en vez de `kernel32.dll`.

---

## 6. Los mosaicos, y el paquete

**Tus mosaicos**: cuatro imágenes, nueve archivos. Las medidas y lo que es fácil equivocar están
en [`ASSETS.es.md`](ASSETS.es.md):

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
python tools\make_tiles.py --origen <tus 4 PNG> --salida C:\dkr\mosaicos
```

**Empaquetar y firmar.** La versión tiene que ser **mayor** que la instalada en la consola:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
python tools\package_uwp.py --version 0.1.1.0 `
       --exe C:\dkr\build-uwp\mdkr64.exe `
       --rom "<tu ROM>.z64" `
       --dawn-bin <uwp-dep>\x64\bin `
       --sdl2-bin C:\sdl2-uwp\SDL2-2.32.10\VisualC-WinRT\x64\Release\SDL-UWP `
       --assets C:\dkr\mosaicos `
       --salida C:\dkr\salida `
       --certificado <tu huella>
```

Verifica el SHA-256 de la ROM **antes** de copiar nada, arma el contenido del paquete, llama a
`makeappx` y firma con `signtool`. Resultado: `DiddyKongRacing_0.1.1.0_x64.msix`, unos 28 MB.

> **La ROM viaja dentro del paquete.** Son 12 MB, caben de sobra, y así desaparecen un paso manual
> y un modo de fallo: arrancar sin datos y quedarse mirando una pantalla negra. La revisión se
> comprueba aquí, en tu PC, porque en una consola no se puede leer el error.

---

## 7. Instalarlo en la consola

Necesitas la dirección del Device Portal de la consola, que muestra Dev Home. El usuario y la
contraseña son los que definiste en **Dev Home → Remote Access Settings**.

El juego declara una dependencia de **Microsoft.VCLibs.140.00**, que la consola tiene que tener
instalada. El `Microsoft.VCLibs.x64.14.00.appx` sale del SDK de Windows (bajo
`Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Retail\x64\`) o de la
distribución de App Installer de Microsoft.

### Antes de tocar nada: cómo tiene que estar la consola

- **En modo desarrollador**, con Dev Home instalado. Si no lo está, eso es un trámite aparte con
  Microsoft y no lo cubre esta guía.
- **Encendida y con tu perfil iniciado.** ⚠ Sin un usuario conectado, la consola **no abre
  aplicaciones**: el paquete se instala, aparece en la lista y al lanzarlo no pasa nada. Es de las
  cosas que más tiempo cuestan averiguar.
- **En la misma red que tu PC.**
- **Su dirección**, que te la dice **Dev Home** en la propia consola. El Device Portal escucha en
  el puerto **11443** por HTTPS.
- **Usuario y contraseña del portal**: los que definiste en **Dev Home → Remote Access Settings**
  al activar el acceso remoto.

**Con el navegador:**

1. Abre `https://<IP de la consola>:11443` en el navegador de tu PC.

   ⚠ El navegador avisará de que **el certificado del sitio no es de confianza**. Es normal y no
   es un problema: ese certificado es de la propia consola, que se lo hace ella. Entra de todas
   formas — en Edge y en Chrome, **Avanzado** → **Continuar a … (no seguro)**; en Firefox,
   **Avanzado** → **Aceptar el riesgo y continuar**. Después te pedirá el usuario y la contraseña
   del portal.
2. **Home → My games & apps → Add**.
3. Elige el `.msix` como paquete y el `.appx` de VCLibs como dependencia.
4. **Start**.

**Con la API REST**, si prefieres automatizarlo: el punto de entrada es
`POST /api/app/packagemanager/package`, multipart.
⚠ Dos cosas que ahí cuestan tiempo: el **boundary del multipart no puede ir entre comillas** (uno
entrecomillado devuelve 500), y las subidas por encima de unos 256 MB fallan — aquí no es
problema, con 28 MB.

⚠ **`Success` no quiere decir instalado.** El portal repite el resultado de la operación anterior.
La instalación terminó cuando el juego aparece en la lista de paquetes (en las pruebas tardó 8
segundos). Mira la lista, no el valor de retorno.

⚠ **La misma versión no reemplaza.** Una versión *mayor* instalada encima actualiza y conserva las
partidas. Desinstalar antes las borra.

> **La consola no te va a pedir el certificado con el que firmaste.** En modo desarrollador
> instala cualquier paquete que venga firmado, sin necesidad de conocer a quien firma: la pantalla
> **Add** ni siquiera tiene casilla para él. El certificado hizo falta en tu PC, para firmar
> (§3), y ahí se acaba su papel.
>
> Si alguna vez el portal rechazara la firma, lo que hay que registrar en la consola es la **parte
> pública** de tu certificado —un archivo `.cer`—, que se saca del propio paquete:
>
> ```powershell
> (Get-AuthenticodeSignature -LiteralPath "<tu .msix>").SignerCertificate |
>     Export-Certificate -FilePath "$env:USERPROFILE\Desktop\firma.cer"
> ```

Después ábrelo con el mando, desde **Mis juegos y aplicaciones**.

---

### Quitarlo de la consola

⚠ **Se van tus partidas.** Viven dentro del paquete, en su `LocalState`, y desaparecen con él. Si
quieres conservarlas, bájalas antes desde el **File explorer** del Device Portal: están en
`LocalState\mdkr64\mdkr64\save`.

Para desinstalar, en el Device Portal: **My games & apps**, busca el juego en la lista, y
**Remove**. Nada de tu PC se toca: el `.msix`, el proyecto y tu ROM siguen donde estaban.

Reinstalar después empieza de cero, con las partidas en blanco. Para **actualizar** sin perderlas
no hay que desinstalar, como dice el aviso de más arriba: basta instalar encima un paquete con una
versión mayor, que es el `--version` que le pasas a `package_uwp.py` (§6).

---

## 8. El primer arranque, y qué mirar

- **B frena y retrocede. No cierra el juego.** Para salir, el botón Xbox: es deliberado
  ([`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md) §6).
- **R3** (pulsar el stick derecho) muestra y oculta el contador de FPS. En consola arranca
  encendido.
- El juego simula a **30 actualizaciones por segundo**, porque esa es la cadencia del juego de
  N64 y no una limitación de este port. Se pueden **presentar** 60: ver más abajo.

### Ponerlo a 60 FPS presentados

El juego **simula** a 30 actualizaciones por segundo y eso no se toca: es la cadencia del juego de
N64 y de ella dependen las físicas y el reloj de carrera. Lo que sí se puede subir es cuántas
imágenes se **presentan**, reconstruyendo las intermedias. El resultado se mueve como a 60 sin
adelantar físicas, entrada ni temporizadores.

> **Esto no es un mod de este repositorio.** Es una opción del propio Golden Balloon, cuyo diseño
> se titula *«Original gameplay with modern presentation»*. Lo que aporta este port es la forma de
> activarla **en una consola**, porque allí el archivo de ajustes del juego no se lee.

Se hace con un archivo de texto. Con el juego ya instalado al menos una vez:

1. Abre el Device Portal de la consola en el navegador y ve al explorador de archivos de la
   aplicación (**File explorer**), dentro de `LocalState\mdkr64\mdkr64\`.
2. Sube ahí un archivo llamado **`diagnostico.txt`** con estas dos líneas:

```text
MDKR_PRESENT_RATE=60
MDKR_PRESENT_SMOOTHING=interpolate
```

3. Cierra el juego del todo y vuelve a abrirlo.

Pulsa **R3** y el contador debería marcar 60.

⚠ **Pon el número, no la palabra `display`.** La consola no informa del refresco de la tele, así
que con `display` la política se queda sin límite y presenta tan rápido como puede: en las pruebas
marcaba 88-90 en vez de 60. Si tu tele va a 120, pon `120`.

Para comprobarlo de verdad, mira `registro.txt` en esa misma carpeta: tiene que decir
`policy=capped rate=60`. Borrar el `diagnostico.txt` lo devuelve todo a como estaba.

Si algo va mal, el registro del propio juego está en
`LocalState\mdkr64\mdkr64\registro.txt`, y se baja con el explorador de archivos del Device
Portal. Ese archivo es lo más útil que hay en la consola: ahí van el adaptador de WebGPU elegido,
la validación de la ROM y el callback `[webgpu] device error` de Dawn.

---

## 9. Cuando algo falla

| Lo que ves | Qué es |
|---|---|
| Un parche se detiene con «el ancla aparece 0 veces» | Tu árbol no es el `v1.7.0`, o ya estaba modificado. El mensaje nombra el archivo y el ancla. No se escribió nada |
| `falta el entorno «store»` | Se lanzó `build_uwp.py` a pelo. Usa `tools\build-uwp.ps1`, que lo carga |
| ~1300 símbolos sin resolver desde zstd | Las cabeceras de clang perdieron contra las de Visual Studio. [`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md) §3.3 |
| `verify_uwp.py` dice que no hay `APPCONTAINER` | Se enlazó sin `/APPCONTAINER`, o con el entorno de escritorio |
| Instala pero «Failed to launch the application» | Casi siempre es el CRT: un binario de escritorio, o la dependencia VCLibs sin instalar en la consola. Pasa antes `verify_uwp.py` |
| Arranca y muere al instante, sin nada en pantalla | Activa los volcados de fallo en el Device Portal, lanza y baja el `.dmp`. Así se encontró el §3.4 |
| La consola sigue mostrando la versión vieja | La versión no subió, o se editó el `Version=` de la plantilla del manifiesto (§3) |
| Los modelos no se ven pero el texto sí | `patch_attributes.py` no se aplicó. [`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md) §3.1 |
