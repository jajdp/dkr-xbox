#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica el port UWP completo a un árbol de Golden Balloon (Diddy Kong Racing).

Uso:
    python tools/apply_uwp.py <raíz del árbol de Golden Balloon>
    python tools/apply_uwp.py --list

La raíz es la carpeta con CMakeLists.txt y platform/main_pc.c. Son dos cosas:

  1. **La capa UWP**, cuatro archivos que no existen en el árbol y se copian a platform/uwp/: la
     entrada WinRT, la capa de compatibilidad y las dos cabeceras POSIX que el CRT de MSVC no
     trae. Son propios del port, así que se copian enteros en vez de parchearse.

  2. **Cinco parches** sobre el árbol del juego, uno por tema. Cada uno es idempotente y
     comprueba lo que espera encontrar antes de escribir, así que pasarlo dos veces no cambia
     nada y, si un parche no reconoce el árbol, se detiene ahí en vez de dejarlo a medias.

Nada de esto compila: después van tools/build-uwp.ps1 (compila y enlaza) y tools/package_uwp.py
(empaqueta y firma). Paso a paso: docs/INSTALL.es.md.

Recompilaciones — https://github.com/jajdp/dkr-xbox
MIT (ver LICENSE)
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERR = os.path.join(REPO, 'tools')
FUENTES = os.path.join(REPO, 'src')

sys.path.insert(0, HERR)
import parchear  # noqa: E402  (tiene que ir después de poner tools/ en la ruta)

# La versión con la que se construyó y probó el port. Se avisa si el árbol es otra, pero no se
# impide seguir: los parches comprueban sus propias anclas, que es la condición que de verdad
# importa, y el upstream se mueve rápido.
VERSION_PROBADA = 'v1.7.0'
PROYECTO_BASE = 'akratch/goldenballoon'

# Los cuatro archivos de la capa UWP: del repositorio a <árbol>/platform/uwp/.
CAPA_UWP = ('uwp_entry.cpp', 'uwp_compat.h', 'dirent.h', 'strings.h')

# El orden no es crítico —ningún parche depende del texto que escriba otro—, pero se mantiene el
# de la historia del port: primero lo que impide compilar, después lo que impide arrancar y al
# final lo que se añade.
PASOS = [
    ('patch_display_list.py', 'el layout del display list, portable entre GCC y MSVC'),
    ('patch_attributes.py',   'los __attribute__ que clang anulaba en silencio al emular a MSVC'),
    ('patch_crt.py',          'el setvbuf que mata el arranque y el sprintf que rompe el enlace'),
    ('patch_webgpu.py',       'WebGPU sobre la CoreWindow, y la rama Dawn de la costura'),
    ('patch_fps_counter.py',  'el contador de FPS en pantalla, que R3 enciende y apaga'),
]

# Los pasos informan en castellano, con acentos, y la consola de Windows arranca en una página de
# códigos que no los tiene (cp1252 o cp850): sin esto, imprimir el informe de un paso levanta un
# UnicodeEncodeError y el port se queda a medio aplicar. Se arregla aquí, para la salida propia, y
# en el entorno de los subprocesos, para la suya.
#
# Y con line_buffering: sin eso, lo que imprime este script se queda en el buffer mientras los
# parches, que son procesos aparte, escriben directos a la consola, y el informe sale al revés —
# los cinco «ya estaba aplicado» antes de los títulos que los anuncian.
for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, 'reconfigure'):
        flujo.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
ENTORNO_HIJOS = dict(os.environ, PYTHONIOENCODING='utf-8:replace', PYTHONUTF8='1')


def version_del_arbol(raiz):
    """La etiqueta que describe el árbol, si es un clon de git. None si no se puede saber."""
    try:
        r = subprocess.run(['git', 'describe', '--tags'], cwd=raiz, capture_output=True,
                           text=True, errors='replace', timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def copia_capa(raiz):
    """Copia los cuatro archivos de la capa UWP. Devuelve los que cambiaron."""
    destino_dir = os.path.join(raiz, 'platform', 'uwp')
    os.makedirs(destino_dir, exist_ok=True)
    cambiados = []
    for nombre in CAPA_UWP:
        origen = os.path.join(FUENTES, nombre)
        if not os.path.isfile(origen):
            sys.exit('falta en el repositorio: %s' % origen)
        with open(origen, 'rb') as f:
            fuente = f.read()
        destino = os.path.join(destino_dir, nombre)
        actual = None
        if os.path.isfile(destino):
            with open(destino, 'rb') as f:
                actual = f.read()
        if actual != fuente:
            with open(destino, 'wb') as f:
                f.write(fuente)
            cambiados.append('platform/uwp/' + nombre)
    return cambiados


def main():
    if '--list' in sys.argv[1:]:
        print('El port UWP, en orden:\n')
        print('  %-26s %s' % ('(la capa UWP)',
                              'src/*.{cpp,h} -> <árbol>/platform/uwp/  (%s)' % ', '.join(CAPA_UWP)))
        for n, (script, que) in enumerate(PASOS, 1):
            print('  %d. %-23s %s' % (n, script, que))
        print('\nDespués: tools/build-uwp.ps1 y tools/package_uwp.py (docs/INSTALL.es.md).')
        return 0

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) != 1:
        sys.exit('uso: %s <ruta de la raíz del árbol de Golden Balloon>   (--list para ver los pasos)'
                 % os.path.basename(sys.argv[0]))
    raiz = parchear.comprueba(args[0])

    version = version_del_arbol(raiz)
    print('árbol  : %s' % raiz)
    print('versión: %s' % (version or '(no es un clon de git: no se puede saber)'))
    if version and not version.startswith(VERSION_PROBADA):
        print('\n⚠ El port se construyó y probó sobre %s de %s. Este árbol es otro.'
              % (VERSION_PROBADA, PROYECTO_BASE))
        print('  Se sigue igualmente: cada parche comprueba sus propias anclas y se detiene si el')
        print('  árbol no es el que espera, que es la condición que de verdad importa.')
    print()

    # La capa UWP. Va sin número, igual que en --list: no es un parche, son archivos nuevos.
    cambiados = copia_capa(raiz)
    print('(la capa UWP: %d archivos)' % len(CAPA_UWP))
    if cambiados:
        for c in cambiados:
            print('      %s' % c)
    else:
        print('      ya estaba al día')

    # Los parches, en orden y numerados como en --list. Si uno falla, se para: el árbol queda con
    # lo aplicado hasta ahí, que es consistente, porque cada parche es todo o nada.
    for n, (script, que) in enumerate(PASOS, 1):
        ruta = os.path.join(HERR, script)
        if not os.path.isfile(ruta):
            sys.exit('falta en el repositorio: %s' % ruta)
        print('%d. %s' % (n, que))
        r = subprocess.run([sys.executable, ruta, raiz], env=ENTORNO_HIJOS)
        if r.returncode != 0:
            print('\n  %s se detuvo. El árbol tiene lo aplicado hasta aquí y nada a medias.'
                  % script)
            print('  Si el árbol no es %s de %s, esa es la causa más probable.'
                  % (VERSION_PROBADA, PROYECTO_BASE))
            return r.returncode

    print()
    print('listo. Ahora:')
    print('  1. configura las dos builds de escritorio   (docs/INSTALL.es.md §4)')
    print('  2. tools/build-uwp.ps1 ... -Enlazar          (§5)')
    print('  3. tools/make_tiles.py y tools/package_uwp.py (§6)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
