# -*- coding: utf-8 -*-
"""Compila y enlaza Golden Balloon para UWP: recompila con ABI de MSVC y enlaza con ld.lld.

EL METODO: traducir la build de escritorio, no mantener otra.

El juego se compila normalmente con MinGW y CMake. Mantener a mano un segundo proyecto para la
consola significa que cada archivo que el upstream anada haya que anadirlo tambien aqui, y el port
se queda atras en semanas. Lo que hace este script es otra cosa: lee de la build de escritorio las
ordenes de compilacion EXACTAS que CMake ya emitio -- una por unidad, en compile_commands.json --,
las traduce al dialecto de la consola y las ejecuta. Un archivo nuevo del upstream entra solo.

Que hace, por pasos:

  1. Lee de build.ninja que objetos entran en mdkr64.exe: los suyos y los de las bibliotecas
     estaticas que se construyen en el arbol.
  2. Busca la orden de compilacion de cada uno en compile_commands.json.
  3. Traduce cada orden de MinGW a MSVC-UWP (las reglas estan abajo, cada una con su motivo).
  4. Compila en paralelo y, si algo falla, agrupa los errores por tipo en vez de volcar miles de
     lineas.
  5. Con --enlazar, llama a ld.lld contra el CRT «store», que es el unico que la Xbox acepta
     dentro de un AppContainer.

⚠ NO se lanza a pelo: hace falta el entorno «store» de Visual Studio (vcvarsall.bat x64 store).
Sin el, INCLUDE y LIB apuntan a las bibliotecas de escritorio y el binario que salga no vale para
nada. Lo carga tools/build-uwp.ps1, que es el punto de entrada normal.

Uso (todo por parametro; no hay ninguna ruta de ninguna maquina escrita aqui):

    python tools/build_uwp.py --raiz <arbol de Golden Balloon>
                              --toolchain <llvm-mingw>/bin
                              --dawn <uwp-dep>/x64
                              --sdl2 <SDL2-2.32.10>
                              [--salida <carpeta>] [--enlazar] [--trabajos N]

De donde sale cada dependencia: docs/DEPENDENCIES.md.

Recompilaciones — https://github.com/jajdp/dkr-xbox
MIT (ver LICENSE)
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Los informes llevan acentos y la consola de Windows arranca en una pagina de codigos que no los
# tiene (cp1252 o cp850): sin esto, imprimir el resumen levanta un UnicodeEncodeError a mitad de
# una compilacion de veinte minutos.
for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, 'reconfigure'):
        flujo.reconfigure(encoding='utf-8', errors='replace')

TARGET = 'x86_64-pc-windows-msvc'

# --- lo que se le anade a TODA unidad -----------------------------------------------------------
DEFS_UWP = [
    '-DWINAPI_FAMILY=WINAPI_FAMILY_APP',   # las cabeceras esconden lo que un AppContainer no puede usar
    '-D_WIN32_WINNT=0x0A00',
    '-D_CRT_SECURE_NO_WARNINGS',
    '-D__WINRT__',                         # SDL2 lo usa para elegir su backend WinRT
    '-DMDKR_DAWN_NATIVE',                  # la rama Dawn de gfx_webgpu_compat.h (patch_webgpu.py)
    '-DMDKR_UWP=1',                        # deja fuera lo que solo vale en escritorio
]

# Banderas de MinGW que no significan nada con ABI de MSVC, o que solo estorban.
#
# -Werror se cae a proposito: aqui interesa ver TODOS los errores duros de una pasada, no parar en
#   la primera advertencia que MSVC emite y MinGW no.
# -mno-ms-bitfields: clang lo RECHAZA con ABI de MSVC («Itanium-compatible layout for the
#   Microsoft C++ ABI is not yet supported»). Quitarlo es seguro SOLO con patch_display_list.py
#   aplicado: ese parche iguala los tipos de los campos de bits de Gpopmtx y Gsetcolor, y el
#   volcado de -fdump-record-layouts sale identico campo a campo bajo las dos reglas. Sin el, la
#   union Gfx pasa de 8 a 16 bytes y el display list se desincroniza entero.
# -fno-keep-inline-dllexport: bandera de GCC que clang no conoce.
FUERA = {'-static-libgcc', '-static-libstdc++', '-municode', '-mwindows',
         '-mno-ms-bitfields', '-fno-keep-inline-dllexport',
         '-Wall', '-Wextra', '-Werror', '-w'}
FUERA_PREFIJO = ('-Werror=', '-Wno-', '--target=')

# Defines que CMake dedujo probando el sistema CON MinGW y que con el CRT de MSVC son mentira.
# harfbuzz se los cree y acaba haciendo #include <pthread.h>, que no existe. Quitandolos toma su
# propio camino nativo de Windows (atomicos e InitOnce del SDK), que es el que corresponde aqui.
FUERA_POSIX = {'-DHAVE_PTHREAD', '-DHAVE_UNISTD_H', '-DHAVE_MPROTECT',
               '-DHAVE_GETPAGESIZE', '-DHAVE_SYS_MMAN_H'}

# Fuentes que en UWP hay que cambiar por otra, no parchear.
#
# a11y_speech_win.cpp habla por SAPI 5 (ISpVoice), que es API de escritorio: WINAPI_FAMILY_APP la
# esconde entera. El proyecto ya trae el backend que corresponde -- a11y_speech_null.c, «text-only,
# and says so» -- que es la respuesta honesta mientras no se escriba uno sobre
# Windows.Media.SpeechSynthesis, que es la via de UWP y es otro tramo de trabajo.
SUSTITUIR_FUENTE = {'platform/a11y_speech_win.cpp': 'platform/a11y_speech_null.c'}

# Includes que hay que sustituir, no arrastrar. Se reconocen por el FINAL de la ruta, no por la
# ruta entera: asi da igual donde tenga cada quien su MSYS2 y su carpeta de build.
SUSTITUIR_INC_SUFIJO = (
    ('/include/sdl2', 'sdl2'),                   # el SDL2 de MinGW -> el de WinRT
    ('/wgpu_native-src/include', 'dawn'),        # wgpu-native -> Dawn
)

# Fuentes que solo existen en el port y por tanto no estan en compile_commands.json: se les
# sintetiza una orden con las mismas banderas base que a todo lo demas.
EXTRAS = [('platform/uwp/uwp_entry.cpp', 'CMakeFiles/mdkr64.dir/platform/uwp/uwp_entry.cpp.obj')]
BASE_EXTRA = ['-O3', '-DNDEBUG', '-std=gnu++17', '-ffp-contract=off',
              '-DSDL_MAIN_HANDLED', '-DNATIVE_PORT=1', '-DMODERN_CC']


def normaliza(p):
    return str(p).replace('\\', '/')


# --- inventario: que objetos entran en el ejecutable --------------------------------------------
def objetos_del_exe(build_dir):
    """Lee build.ninja y devuelve los objetos de mdkr64.exe, los suyos y los de sus .a.

    Esto lo hacia antes un script aparte que dejaba un .json a mano. Va aqui porque es parte de la
    receta: sin el inventario no hay nada que traducir, y un .json guardado envejece en cuanto el
    upstream anade un archivo.
    """
    texto = (build_dir / 'build.ninja').read_text(encoding='utf-8', errors='replace')
    aristas = {}
    for linea in texto.splitlines():
        if not linea.startswith('build '):
            continue
        cuerpo = linea[len('build '):]
        if ':' not in cuerpo:
            continue
        salidas, resto = cuerpo.split(':', 1)
        piezas = resto.split()
        if not piezas:
            continue
        entradas = []
        for p in piezas[1:]:
            if p == '||':          # dependencias de orden: no entran al enlace
                break
            if p == '|':           # implicitas: aqui viven los .a
                continue
            entradas.append(p)
        for s in salidas.split():
            aristas[normaliza(s)] = entradas

    entradas = aristas.get('mdkr64.exe')
    if entradas is None:
        sys.exit('build.ninja no declara mdkr64.exe: ¿es la carpeta de build correcta?')
    propios = [e for e in entradas if e.endswith('.obj')]
    de_libs = []
    for lib in [e for e in entradas if e.endswith('.a')]:
        de_libs += [e for e in aristas.get(normaliza(lib), []) if e.endswith('.obj')]
    return propios + de_libs


def carga_ordenes(build_dir):
    """obj (normalizado) -> entrada de compile_commands.json."""
    ruta = build_dir / 'compile_commands.json'
    if not ruta.is_file():
        sys.exit('falta %s: configura esa build antes (docs/INSTALL.es.md §4)' % ruta)
    por = {}
    for e in json.loads(ruta.read_text(encoding='utf-8', errors='replace')):
        m = re.search(r'-o\s+(\S+\.obj)', e['command'])
        if m:
            por[normaliza(m.group(1))] = e
    return por


# --- traduccion de una orden --------------------------------------------------------------------
def traduce(cfg, entrada, obj_rel):
    """Convierte una orden de MinGW en la orden UWP equivalente. Devuelve (argv, salida)."""
    toks = shlex.split(entrada['command'], posix=False)
    fuente = Path(entrada['file'])
    rel = normaliza(fuente)
    for viejo, nuevo in SUSTITUIR_FUENTE.items():
        if rel.endswith(viejo):
            fuente = cfg.raiz / nuevo
    es_cxx = fuente.suffix in ('.cpp', '.cc', '.cxx')

    # -fms-runtime-lib=dll: con ABI de MSVC clang asume el CRT estatico y siembra los objetos con
    #   /DEFAULTLIB:libcpmt, que ni existe para la tienda ni valdria: una app de UWP usa el CRT en
    #   DLL (vcruntime140_app). Esto hace que pida msvcrt/msvcprt, que son los buenos.
    # -g -gcodeview: informacion de depuracion en el formato que entiende el depurador de Windows.
    #   Sin esto, un volcado de la consola solo da «mdkr64+0x11a5ed» y hay que adivinar. Cuesta
    #   tamano en disco y nada en velocidad, y aqui cada ciclo de prueba pasa por instalar en la
    #   consola: el primer fallo del port se encontro justo asi.
    # -fdebug-compilation-dir / -fcoverage-compilation-dir: clang escribe en la informacion de
    #   depuracion el DIRECTORIO ACTUAL del proceso, no el del arbol. Sin fijarlo, compilar desde
    #   C:\ y desde otra carpeta produce objetos distintos byte a byte --y por tanto ejecutables
    #   distintos-- con el mismo codigo. Costo media prueba de reproducibilidad descubrirlo:
    #   dos arboles identicos daban .text de distinto tamano. Con un valor constante, el binario
    #   solo depende de las fuentes y del toolchain, que es lo que se quiere poder comparar.
    argv = [str(cfg.clangxx if es_cxx else cfg.clang), '--target=' + TARGET,
            '-fms-runtime-lib=dll', '-g', '-gcodeview',
            '-fdebug-compilation-dir=.', '-fcoverage-compilation-dir=.']
    saltar = False
    for t in toks[1:]:
        if saltar:
            saltar = False
            continue
        if t in ('-o', '-c'):
            saltar = (t == '-o')
            continue
        if t.endswith(('.obj', '.c', '.cpp', '.cc')):
            continue
        if t in FUERA or t in FUERA_POSIX or t.startswith(FUERA_PREFIJO):
            continue
        if t.startswith('-I'):
            argv.append('-I' + sustituye_include(cfg, t[2:].strip('"')))
            continue
        if t.startswith('-D'):
            # En compile_commands.json las comillas de un define van escapadas para la linea de
            # ordenes de ninja. Aqui el argumento se le pasa DIRECTO al proceso, asi que hay que
            # deshacer ese escapado: si no, el juego recibe MDKR_VERSION_STRING=\"1.7.0\" con las
            # barras dentro y el preprocesador no puede con ello.
            argv.append(t.replace(chr(92) + '"', '"'))
            continue
        if t == '-std=gnu++11':
            # harfbuzz moderno usa tipos de retorno deducidos, que son de C++14. GCC los pasa como
            # extension y clang no. El proyecto lo compila con gnu++11 por el defecto de CMake;
            # subirlo a gnu++17 es lo que ya hace con el resto del C++ del arbol.
            argv.append('-std=gnu++17')
            continue
        argv.append(t)

    argv += DEFS_UWP
    argv += ['-I', str(cfg.raiz / 'platform' / 'uwp'),   # dirent.h y strings.h propios: PRIMERO
             '-I', str(cfg.dawn_inc),
             '-I', str(cfg.sdl2_inc)]
    argv += ['-include', str(cfg.raiz / 'platform' / 'uwp' / 'uwp_compat.h')]

    # Las cabeceras propias de clang van DELANTE de las de MSVC. No es cosmetica: Visual Studio
    # trae su propio emmintrin.h que solo DECLARA las intrinsecas SSE2 (su compilador las resuelve
    # en el backend), mientras que el de clang las DEFINE como static inline. Si gana el de MSVC,
    # clang emite llamadas de verdad a _mm_loadu_si128 y companyia, y el enlace se cae con 1300
    # referencias sin dueno desde zstd. Con clang-cl esto lo resolveria -imsvc, que este driver no
    # acepta; el orden explicito hace lo mismo.
    argv += ['-isystem', str(cfg.resource_dir / 'include')]

    # Las cabeceras del SDK y del CRT «store» llegan por INCLUDE, que pone vcvarsall.
    for d in os.environ.get('INCLUDE', '').split(';'):
        if d.strip():
            argv += ['-isystem', d.strip()]

    salida = cfg.salida / obj_rel
    salida.parent.mkdir(parents=True, exist_ok=True)
    argv += ['-c', str(fuente), '-o', str(salida)]
    return argv, salida


def sustituye_include(cfg, ruta):
    """Cambia los includes de MinGW por los de la consola, reconociendolos por el final."""
    n = normaliza(ruta).rstrip('/').lower()
    for sufijo, cual in SUSTITUIR_INC_SUFIJO:
        if n.endswith(sufijo):
            return str(cfg.sdl2_inc if cual == 'sdl2' else cfg.dawn_inc)
    return ruta


# --- enlace -------------------------------------------------------------------------------------
def enlaza(cfg, objs):
    print()
    print('=== enlace con ld.lld contra el CRT «store» ===')
    exe = cfg.salida / 'mdkr64.exe'
    argv = [str(cfg.lld), '-flavor', 'link', '/nologo', '/machine:x64', '/subsystem:windows',
            '/APPCONTAINER',                 # el bit sin el cual la consola no activa la app
            '/manifest:no', '/opt:ref',
            '/DEBUG', '/PDB:%s' % exe.with_suffix('.pdb'),   # el .pdb se queda aqui, no va al paquete
            '/out:%s' % exe]
    for d in os.environ.get('LIB', '').split(';'):
        if d.strip():
            argv.append('/libpath:' + d.strip())
    argv += ['/libpath:%s' % cfg.dawn_lib, '/libpath:%s' % cfg.sdl2_lib]
    argv += [str(o) for o in objs]
    argv += [
        'SDL2.lib', 'webgpu_dawn.lib',
        'WindowsApp.lib', 'OneCore.lib', 'ntdll.lib', 'dxgi.lib', 'ws2_32.lib',
        'runtimeobject.lib',               # RoInitialize, para el apartamento MTA de la entrada
        # CRT «store»: el _app es el unico que la consola acepta
        'msvcrt.lib', 'msvcprt.lib', 'vcruntime.lib', 'ucrt.lib',
        # Residuo de un intento abandonado: era la companyera obligada de _NO_CRT_STDIO_INLINE,
        # que fue el primer rodeo para el choque de sprintf y que no funciono (patch_crt.py
        # cuenta por que). Aqui ya no hace falta, pero el binario que se probo en la consola se
        # enlazo con ella y quitarla es un cambio que nadie ha medido: se deja hasta que alguien
        # compruebe que el enlace sale igual sin ella.
        'legacy_stdio_definitions.lib',
    ]
    r = subprocess.run(argv, capture_output=True, text=True, errors='replace')
    salida = (r.stdout or '') + (r.stderr or '')
    informe = cfg.salida / 'enlace.txt'
    informe.write_text(salida, encoding='utf-8')
    if r.returncode == 0:
        print('  ENLAZA. %s  (%.1f MB)' % (exe, exe.stat().st_size / 1048576))
        return 0
    faltan = sorted(set(re.findall(r'undefined symbol: (.+)', salida)))
    print('  no enlaza: %d símbolos sin resolver' % len(faltan))
    for s in faltan[:60]:
        print('   %s' % s)
    if len(faltan) > 60:
        print('   … y %d más' % (len(faltan) - 60))
    otros = [l for l in salida.splitlines()
             if 'error' in l.lower() and 'undefined symbol' not in l]
    if otros:
        print()
        print('=== otros errores del enlazador ===')
        for l in otros[:20]:
            print('   %s' % l[:140])
    print()
    print('  detalle completo en %s' % informe)
    return 1


# --- configuracion --------------------------------------------------------------------------------
class Config:
    def __init__(self, a):
        self.raiz = Path(a.raiz).resolve()
        toolchain = Path(a.toolchain).resolve()
        self.clang = toolchain / 'clang.exe'
        self.clangxx = toolchain / 'clang++.exe'
        self.lld = toolchain / 'ld.lld.exe'
        self.resource_dir = resource_dir(toolchain)
        dawn = Path(a.dawn).resolve()
        self.dawn_inc, self.dawn_lib = dawn / 'include', dawn / 'lib'
        sdl2 = Path(a.sdl2).resolve()
        self.sdl2_inc = sdl2 / 'include'
        self.sdl2_lib = sdl2 / 'VisualC-WinRT' / 'x64' / 'Release' / 'SDL-UWP'
        self.salida = Path(a.salida).resolve() if a.salida else self.raiz / 'build-uwp'
        self.build = self.raiz / a.build
        self.build_deps = self.raiz / a.build_deps

        falta = [str(p) for p in (self.clang, self.clangxx, self.lld,
                                  self.dawn_inc, self.dawn_lib, self.sdl2_inc, self.sdl2_lib)
                 if not p.exists()]
        if falta:
            sys.exit('no se encuentra:\n  ' + '\n  '.join(falta) +
                     '\n(de dónde sale cada pieza: docs/DEPENDENCIES.md)')


def resource_dir(toolchain):
    """La carpeta de cabeceras propias de clang, sea cual sea su versión."""
    base = toolchain.parent / 'lib' / 'clang'
    versiones = sorted((d for d in base.glob('*') if d.is_dir()),
                       key=lambda d: [int(x) if x.isdigit() else 0 for x in d.name.split('.')])
    if not versiones:
        sys.exit('no hay cabeceras de clang en %s' % base)
    return versiones[-1]


def main():
    p = argparse.ArgumentParser(
        description='Compila y enlaza Golden Balloon para UWP (Xbox Series en modo desarrollador).',
        epilog='Se lanza desde tools/build-uwp.ps1, que carga el entorno «store» de Visual Studio.')
    p.add_argument('--raiz', required=True, help='raíz del árbol de Golden Balloon, ya parcheado')
    p.add_argument('--toolchain', required=True, help='carpeta bin de llvm-mingw (clang, ld.lld)')
    p.add_argument('--dawn', required=True, help='carpeta x64 de uwp-dep (include y lib de Dawn)')
    p.add_argument('--sdl2', required=True, help='raíz de las fuentes de SDL2, ya compilado para WinRT')
    p.add_argument('--salida', help='carpeta de salida (por omisión, <raíz>/build-uwp)')
    p.add_argument('--build', default='build-sin-lanzador',
                   help='build de escritorio SIN lanzador, de la que salen los objetos y sus órdenes')
    p.add_argument('--build-deps', default='build',
                   help='build de escritorio completa, donde viven harfbuzz y SheenBidi')
    p.add_argument('--enlazar', action='store_true', help='enlazar si todo compila')
    p.add_argument('--trabajos', type=int, default=0, help='compilaciones en paralelo (por omisión, los núcleos)')
    a = p.parse_args()

    if not os.environ.get('INCLUDE'):
        sys.exit('falta el entorno «store» de Visual Studio.\n'
                 'Lanza tools/build-uwp.ps1, no este script a pelo (docs/INSTALL.es.md §5).')

    cfg = Config(a)
    ordenes_sl = carga_ordenes(cfg.build)
    ordenes_ok = carga_ordenes(cfg.build_deps)

    trabajos, sin_orden = [], []
    for o in objetos_del_exe(cfg.build):
        n = normaliza(o)
        e = ordenes_sl.get(n) or ordenes_ok.get(n)
        (trabajos.append((e, n)) if e else sin_orden.append(o))
    # harfbuzz y SheenBidi viven en la build completa (FETCHCONTENT_BASE_DIR apunta alli)
    for n in [o for o in ordenes_ok if 'harfbuzz' in o.lower() or 'sheenbidi' in o.lower()]:
        trabajos.append((ordenes_ok[n], n))
    for fuente, obj_rel in EXTRAS:
        trabajos.append(({'file': str(cfg.raiz / fuente),
                          'command': 'cc ' + ' '.join(BASE_EXTRA)}, obj_rel))

    print('=== construcción UWP de Diddy Kong Racing (Golden Balloon) ===')
    print('  árbol              : %s' % cfg.raiz)
    print('  objetos a compilar : %d' % len(trabajos))
    print('  sin orden conocida : %d  %s' % (len(sin_orden), [Path(s).name for s in sin_orden]))
    print('  salida             : %s' % cfg.salida)
    print()

    t0 = time.time()

    def compila(par):
        entrada, obj_rel = par
        argv, salida = traduce(cfg, entrada, obj_rel)
        r = subprocess.run(argv, capture_output=True, text=True, errors='replace')
        return (obj_rel, entrada['file'], r.returncode, r.stderr, salida)

    resultados = []
    with ThreadPoolExecutor(max_workers=a.trabajos or min(16, os.cpu_count() or 4)) as ex:
        for i, res in enumerate(ex.map(compila, trabajos), 1):
            resultados.append(res)
            if i % 25 == 0:
                print('  %4d/%d   fallan %d'
                      % (i, len(trabajos), sum(1 for x in resultados if x[2] != 0)))

    ok = [r for r in resultados if r[2] == 0]
    mal = [r for r in resultados if r[2] != 0]
    print()
    print('=== compilación: %d bien, %d mal  (%.0f s) ===' % (len(ok), len(mal), time.time() - t0))
    print()

    if mal:
        todos = '\n'.join(r[3] for r in mal)
        informe = cfg.salida / 'errores.txt'
        informe.write_text(todos, encoding='utf-8')
        print('=== archivos que fallan ===')
        for r in mal[:40]:
            print('  %s' % Path(r[1]).name)
        if len(mal) > 40:
            print('  … y %d más' % (len(mal) - 40))
        print()
        msgs = [re.sub(r"'[^']*'", "'X'", m) for m in re.findall(r'error: (.+)', todos)]
        print('=== errores más repetidos ===')
        for m, n in Counter(msgs).most_common(20):
            print('  %4d  %s' % (n, m[:112]))
        print()
        print('=== símbolos que UWP no declara ===')
        for n in sorted(set(re.findall(r"call to undeclared function '([^']+)'", todos))):
            print('   %s' % n)
        print('=== cabeceras que faltan ===')
        for n in sorted(set(re.findall(r"'([^']+)' file not found", todos))):
            print('   %s' % n)
        print()
        print('  detalle completo en %s' % informe)

    lista = cfg.salida / 'objetos.txt'
    lista.write_text('\n'.join(str(r[4]) for r in ok), encoding='utf-8')
    print('  objetos buenos listados en %s' % lista)

    if a.enlazar:
        if mal:
            print()
            print('  no se enlaza: hay unidades que no compilan.')
            return 1
        return enlaza(cfg, [r[4] for r in ok])
    return 0 if not mal else 1


if __name__ == '__main__':
    sys.exit(main())
