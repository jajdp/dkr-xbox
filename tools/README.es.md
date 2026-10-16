# Las herramientas, y el orden en que van

*(English: [README.md](README.md))*

Once archivos. De verdad solo invocas cuatro, y en este orden:

```text
1. configure-desktop.sh    las dos builds de escritorio, en MSYS2    (INSTALL §4)
2. apply_uwp.py            parchear el árbol                         (INSTALL §5)
3. build-uwp.ps1           compilar y enlazar para la consola        (INSTALL §5)
4. package_uwp.py          armar y firmar el .msix                   (INSTALL §6)
```

Los demás los llaman esos, o están ahí para cuando algo sale mal.

## Qué es cada uno

| | |
|---|---|
| `configure-desktop.sh` | Configura y compila las dos configuraciones de escritorio de las que este port lee. Se corre dentro de **MSYS2 UCRT64**, no en PowerShell. Es el paso largo |
| `apply_uwp.py` | **El punto de entrada.** Copia los cuatro archivos de `src/` a `platform/uwp/` y aplica los cinco parches en orden. Con `--list` enseña los pasos sin tocar nada |
| `parchear.py` | Lo que comparten los parches: leer, comprobar, sustituir y escribir. No se lanza solo. Vale la pena leerlo una vez: es donde están implementados de verdad el «todo o nada» y la idempotencia |
| `patch_display_list.py` | El layout del display list, portable entre GCC y MSVC, para `Gpopmtx` y `Gsetcolor` |
| `patch_attributes.py` | Que los `__attribute__` sobrevivan a clang apuntando a MSVC |
| `patch_crt.py` | El `setvbuf` que mata el arranque, y el `sprintf` del decomp |
| `patch_webgpu.py` | WebGPU sobre una `CoreWindow`, y la rama Dawn de la costura de dialecto |
| `patch_fps_counter.py` | El contador de FPS en pantalla, que R3 enciende y apaga |
| `build-uwp.ps1` | Carga el entorno **store** de Visual Studio y le pasa el trabajo a `build_uwp.py`. Usa este, no el Python directamente |
| `build_uwp.py` | La traducción en sí: lee las órdenes de compilación de la build de escritorio, las reescribe para la consola, compila y enlaza |
| `make_tiles.py` | Tus cuatro imágenes → los nueve mosaicos que el manifiesto necesita |
| `package_uwp.py` | Verifica la ROM, arma el paquete y lo firma |
| `verify_uwp.py` | Comprueba que el binario es UWP de verdad. Pásalo antes de empaquetar |

## Cómo se leen los parches

Cada uno abre con el síntoma, la causa y por qué el arreglo es ese; esa prosa es el valor que
tienen, y [`../docs/HOW-IT-WORKS.es.md`](../docs/HOW-IT-WORKS.es.md) es la misma historia contada
una sola vez, de principio a fin.

Debajo de la prosa está `CAMBIOS`, una lista de tríos:

```python
('platform/main_pc.c',       # el archivo, relativo a la raíz del árbol
 # busca:                    # el texto que el parche busca
 ('...'),
 # queda:                    # el texto que lo sustituye
 ('...')),
```

El texto que cada parche escribe es, carácter por carácter, el que tiene el árbol con el que se
construyó y se probó el port en la consola. Por eso va citado literalmente en vez de generado.

## Tres reglas que cumplen todos

- **Todo o nada.** Cada sustitución se calcula primero en memoria, y no se escribe ninguna hasta
  que todas cuadran. Un parche que toca cinco archivos y tropieza en el cuarto no deja escrito
  ninguno.
- **Idempotentes, y sin marca inyectada.** «Ya aplicado» se decide preguntando si el texto nuevo ya
  está, no por un comentario centinela — así lo que acaba en el árbol es exactamente lo que tiene
  el port que funciona.
- **Escritura atómica, y se conservan los finales de línea del archivo.** Golden Balloon tiene
  archivos con CRLF y archivos con LF, y su `.gitattributes` los gobierna; cambiarlos aquí llenaría
  el `git status` del árbol del juego de archivos que ningún parche tocó.

## Una nota sobre el idioma

Los scripts y los comentarios que escriben llevan su prosa en castellano, que es donde se
escribieron. La documentación va en los dos idiomas. Nada del código que producen depende de ello.
