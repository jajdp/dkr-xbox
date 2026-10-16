#!/usr/bin/env bash
# Configura y compila las DOS builds de escritorio de las que vive el port UWP.
#
# El port no mantiene un segundo proyecto: lee las ordenes de compilacion que CMake ya emitio
# para escritorio y las traduce al dialecto de la consola (tools/build_uwp.py). Por eso hace
# falta tener aqui dos configuraciones, y cada una cumple un papel distinto:
#
#   build/                 la build COMPLETA, y de verdad compilada. De ella salen dos cosas:
#                          las descargas de FetchContent (harfbuzz, SheenBidi, basisu, el
#                          prebuilt de wgpu-native) y las ordenes de compilacion de harfbuzz y
#                          SheenBidi, que la otra configuracion no reconstruye.
#
#   build-sin-lanzador/    la build SIN el shell de escritorio (-DMDKR_APP=OFF). Esta solo se
#                          CONFIGURA, no se compila: de ella se cosecha la lista exacta de
#                          objetos y sus ordenes en la configuracion que de verdad quiere la
#                          consola. Con el lanzador ImGui dentro habria que portar 62 objetos de
#                          C++ mas que en una Xbox no sirven de nada, porque el juego se lanza
#                          desde el panel del sistema y no desde una ventana con raton.
#                          MDKR_APP=OFF es una configuracion soportada por el propio proyecto
#                          (la usa la build de wasm), y en ella main() vuelve a
#                          platform/main_pc.c, que es lo que el arranque WinRT envuelve.
#
# ⚠ SE CORRE DENTRO DE MSYS2 UCRT64, no en el bash de Git ni en PowerShell. UCRT64 y no MINGW64
# porque es lo que usa el CI del propio juego: los ejecutables de MINGW64 enlazan el msvcrt.dll
# antiguo, cuyo fopen rechaza el flag 'x' de C11 del que depende toda escritura atomica de
# ajustes (el proyecto publico una vez un zip asi y no guardaba ninguna preferencia).
#
# ⚠ EL ARBOL TIENE QUE ESTAR EN UNA RUTA SIN ESPACIOS. windres.exe invoca al preprocesador sin
# entrecomillar la ruta, asi que con un arbol en «…\Documentos\Mis cosas\…» falla al compilar
# mdkr64.rc, y solo ese: los otros 1154 objetos compilan bien. C:\dkr sirve de sobra.
#
# NO se pasa -DMDKR_BUILD_TESTS: esa opcion no existe en el proyecto y CMake avisa de que la
# variable no se uso. Los tests no estorban aqui porque esta configuracion no se compila.
#
# El configure necesita red: cmake/webgpu.cmake descarga el prebuilt de wgpu-native y lo
# verifica por SHA-256.
#
# Uso, desde el bash de MSYS2 UCRT64:
#     bash tools/configure-desktop.sh /c/dkr
#
# Paso a paso, con los requisitos: docs/INSTALL.es.md §4.
set -euo pipefail

RAIZ="${1:-}"
if [ -z "$RAIZ" ]; then
  echo "uso: bash tools/configure-desktop.sh <raiz del arbol de Golden Balloon>" >&2
  echo "     (ruta estilo MSYS2, p. ej. /c/dkr)" >&2
  exit 2
fi
if [ ! -f "$RAIZ/CMakeLists.txt" ] || [ ! -f "$RAIZ/platform/main_pc.c" ]; then
  echo "no parece la raiz del arbol de Golden Balloon: $RAIZ" >&2
  exit 2
fi

export PATH="/ucrt64/bin:$PATH"

# CMake deduce CMAKE_SYSTEM_PROCESSOR de PROCESSOR_ARCHITECTURE, y un shell de login de MSYS2
# lanzado desde fuera no la propaga: llega vacia y cmake/webgpu.cmake aborta con
# "no pinned wgpu-native prebuilt for OS='Windows', CPU='', ABI='gnu'".
export PROCESSOR_ARCHITECTURE="${PROCESSOR_ARCHITECTURE:-AMD64}"

cd "$RAIZ"

echo "=== entorno ==="
for t in gcc cmake ninja; do printf '  %-8s ' "$t"; "$t" --version 2>&1 | head -1; done
printf '  %-8s ' "sdl2"; pkg-config --modversion sdl2 2>/dev/null || echo "NO ENCONTRADO"
printf '  %-8s ' "arbol"; echo "$RAIZ"
printf '  %-8s ' "version"; git describe --tags 2>/dev/null || echo "(no es un clon de git)"
echo

# MDKR_NATIVE_PHONE_PARTY viene ON por omision: es el transporte WSS/WebRTC que permite usar el
# movil como mando, y arrastra libdatachannel con sus submodulos. Se apaga por ALCANCE, no por
# esquivar su descarga: el port de consola no lo necesita, y una pila WebRTC con sockets dentro
# de un AppContainer seria un frente aparte.
echo "=== 1/3  configurar la build completa ==="
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DMDKR_NATIVE_PHONE_PARTY=OFF

echo
echo "=== 2/3  compilarla  (es la larga: descarga y construye las dependencias) ==="
cmake --build build -j

echo
echo "=== 3/3  configurar la build sin lanzador (solo configure) ==="
# FETCHCONTENT_BASE_DIR apunta a las descargas de la build de arriba para no volver a bajar
# harfbuzz, SheenBidi, basisu ni el prebuilt de wgpu-native.
cmake -B build-sin-lanzador -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DMDKR_NATIVE_PHONE_PARTY=OFF \
      -DMDKR_APP=OFF \
      -DFETCHCONTENT_BASE_DIR="$RAIZ/build/_deps"

echo
echo "=== resultado ==="
for f in build/compile_commands.json build-sin-lanzador/compile_commands.json \
         build-sin-lanzador/build.ninja; do
  printf '  %-46s ' "$f"
  [ -f "$f" ] && echo "ok" || echo "FALTA"
done
echo
echo "LISTO. Ahora, desde PowerShell: tools\\build-uwp.ps1 (docs/INSTALL.es.md §5)."
