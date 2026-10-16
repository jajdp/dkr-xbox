# -*- coding: utf-8 -*-
"""Comprueba que el binario es UWP de verdad, y no un ejecutable de escritorio con otro nombre.

Vale la pena correrlo antes de empaquetar: un .msix con un binario de escritorio dentro se
instala sin protestar y la consola responde «Failed to launch the application», que no dice nada
de por qué.

Qué se mira, y por qué cada cosa:

  bit APPCONTAINER   Sin él, la consola rechaza el paquete. Lo pone /APPCONTAINER al enlazar.
  subsistema         Tiene que ser GUI de Windows.
  DLL importadas     Una app de la tienda tira de los conjuntos api-ms-win-*, no de kernel32 ni
                     user32 a pelo. Si aparecen esos dos, se compiló con el CRT de escritorio:
                     el entorno era «desktop» y no «store».
  CRT                VCRUNTIME140_APP y compañía, los _app. Los que no llevan _APP son los de
                     escritorio y la consola no los tiene.

Con --referencia se compara contra otro ejecutable UWP que ya se sepa que arranca en la consola,
que es la forma más rápida de ver si falta algo: si los dos coinciden en lo que importa, el
nuestro tiene las mismas papeletas de pasar la validación.

Uso:
    python tools/verify_uwp.py --exe <build-uwp>/mdkr64.exe --toolchain <llvm-mingw>/bin
                               [--referencia <otro .exe UWP que ya funcione>]

Recompilaciones — https://github.com/jajdp/dkr-xbox
MIT (ver LICENSE)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, 'reconfigure'):
        flujo.reconfigure(encoding='utf-8', errors='replace')

# Importar estas dos en una app de la tienda delata el CRT equivocado.
DELATORAS = ('kernel32.dll', 'user32.dll', 'msvcp140.dll', 'vcruntime140.dll')


def datos(exe, objdump, readobj):
    if not exe.is_file():
        return None
    cab = subprocess.run([str(readobj), '--file-headers', str(exe)],
                         capture_output=True, text=True, errors='replace').stdout
    sub = re.search(r'Subsystem: (\S+)', cab)
    dlls = sorted(set(re.findall(r'DLL Name: (\S+)',
                                 subprocess.run([str(objdump), '-p', str(exe)],
                                                capture_output=True, text=True,
                                                errors='replace').stdout)))
    return {
        'tamano': exe.stat().st_size,
        'subsistema': sub.group(1) if sub else '?',
        'appcontainer': 'APPCONTAINER' in cab.upper(),
        'dlls': dlls,
    }


def pinta(titulo, d):
    print('=== %s ===' % titulo)
    print('  tamaño       : %.1f MB' % (d['tamano'] / 1048576))
    print('  subsistema   : %s' % d['subsistema'])
    print('  APPCONTAINER : %s' % ('sí' if d['appcontainer'] else 'NO  <-- la consola lo rechazaría'))
    print('  DLL (%d):' % len(d['dlls']))
    for x in d['dlls']:
        print('      %s' % x)


def main():
    p = argparse.ArgumentParser(description='Comprueba que el binario es UWP de verdad.')
    p.add_argument('--exe', required=True, help='el mdkr64.exe a comprobar')
    p.add_argument('--toolchain', required=True, help='carpeta bin de llvm-mingw (llvm-objdump, llvm-readobj)')
    p.add_argument('--referencia', help='otro ejecutable UWP que ya se sepa que arranca en la consola')
    a = p.parse_args()

    toolchain = Path(a.toolchain)
    objdump, readobj = toolchain / 'llvm-objdump.exe', toolchain / 'llvm-readobj.exe'
    for x in (objdump, readobj):
        if not x.is_file():
            sys.exit('falta %s' % x)

    n = datos(Path(a.exe), objdump, readobj)
    if n is None:
        sys.exit('no existe %s' % a.exe)
    pinta('el binario', n)

    malas = [d for d in n['dlls'] if d.lower() in DELATORAS]
    problemas = []
    if not n['appcontainer']:
        problemas.append('falta el bit APPCONTAINER: ¿se enlazó sin /APPCONTAINER?')
    if malas:
        problemas.append('importa DLL de escritorio (%s): el entorno de Visual Studio era '
                         '«desktop» y no «store»' % ', '.join(malas))

    if a.referencia:
        r = datos(Path(a.referencia), objdump, readobj)
        if r is None:
            print('\n  (no encontré la referencia en %s)' % a.referencia)
        else:
            print()
            pinta('referencia', r)
            solo = [d for d in n['dlls'] if d.lower() not in {x.lower() for x in r['dlls']}]
            print()
            print('=== DLL que pedimos y la referencia no ===')
            for d in solo or ['ninguna']:
                print('      %s' % d)

    print()
    if problemas:
        print('=== PROBLEMAS ===')
        for x in problemas:
            print('  %s' % x)
        return 1
    print('  el binario tiene la forma de una aplicación UWP.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
