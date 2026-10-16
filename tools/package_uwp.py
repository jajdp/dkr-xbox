# -*- coding: utf-8 -*-
"""Arma el .msix del port UWP de Diddy Kong Racing y lo firma.

Que lleva el paquete, y por que:

  mdkr64.exe              el juego, salido de build_uwp.py
  SDL2.dll                la build WinRT de SDL2, NO la de escritorio
  webgpu_dawn.dll         la implementacion de WebGPU
  libuwp.dll              de ella depende webgpu_dawn.dll
  dxcompiler.dll          Dawn la carga en caliente para compilar los sombreadores
  dxil.dll                companyera de la anterior: firma el bytecode que produce
  baserom.us.v80.z64      TU ROM, verificada por SHA-256 antes de copiarla
  Assets\\                 TUS mosaicos (make_tiles.py; docs/ASSETS.md)
  AppxManifest.xml        el manifiesto, con la version que se le pase

MSVCP140_APP, vccorlib140_app y VCRUNTIME140_APP **no** van dentro: llegan por la dependencia
Microsoft.VCLibs.140.00 que declara el manifiesto. Meterlas dentro del paquete hace que se
instale y no arranque (0x8027025B, comprobado con otro port de la casa).

⚠ LA ROM SE VERIFICA AQUI, en el PC, no en la consola. Si se colara la revision equivocada el
juego arrancaria en la Xbox y moriria con un mensaje que nadie puede leer. La huella de referencia
es la de la us.v80, que es la unica que el port acepta; no es contenido de la ROM, es su resumen.

⚠ LA VERSION SUBE EN CADA PAQUETE. La consola no reemplaza un paquete por otro de la MISMA
version: o se desinstala antes, o se cambia el numero.

Uso:

    python tools/package_uwp.py --version 0.1.1.3
                                --exe <build-uwp>/mdkr64.exe
                                --rom <tu ROM .z64>
                                --dawn-bin <uwp-dep>/x64/bin
                                --sdl2-bin <SDL2>/VisualC-WinRT/x64/Release/SDL-UWP
                                --assets <carpeta con tus mosaicos>
                                --salida <carpeta>
                                --certificado <huella SHA-1 de TU certificado>
                                [--sdk <carpeta bin del SDK de Windows>]

Como crear un certificado autofirmado: docs/INSTALL.es.md §3.

Recompilaciones — https://github.com/jajdp/dkr-xbox
MIT (ver LICENSE)
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, 'reconfigure'):
        flujo.reconfigure(encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parent.parent
MANIFIESTO = REPO / 'package' / 'Package.appxmanifest'

ROM_EN_PAQUETE = 'baserom.us.v80.z64'
# us.v80 es la revision 1.1 (en los sets habituales, «(Rev A)»). La 1.0 NO vale: el port la
# rechaza. Esto es una huella, no contenido: aqui no se distribuye ninguna ROM.
ROM_SHA256 = '7de1a8fb2a9558cfc3d9ad4497df698c1e89cf7095ac1531557df2af40ba8bcf'

# La plantilla del manifiesto lleva esta version y el empaquetador la sustituye por la pedida.
# ⚠ Si se cambia en la plantilla, el reemplazo deja de ocurrir y NO avisa: el .msix saldria con el
# nombre de la version pedida y por dentro la de la plantilla, y la consola no lo reemplazaria.
VERSION_PLANTILLA = '0.1.0.0'

DLLS_DAWN = ('webgpu_dawn.dll', 'libuwp.dll', 'dxcompiler.dll', 'dxil.dll')
DLLS_SDL2 = ('SDL2.dll',)

# Los nueve mosaicos que el manifiesto nombra. Los sin calificador de escala tienen que existir
# igual: el paquete se arma sin resources.pri, y entonces makeappx busca el nombre literal.
MOSAICOS = ('Square150x150Logo.png', 'Square150x150Logo.scale-200.png',
            'SplashScreen.png', 'SplashScreen.scale-200.png',
            'Square44x44Logo.png', 'Square44x44Logo.scale-200.png',
            'Square44x44Logo.targetsize-24_altform-unplated.png',
            'StoreLogo.png', 'StoreLogo.scale-200.png')


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for trozo in iter(lambda: f.read(1 << 20), b''):
            h.update(trozo)
    return h.hexdigest()


def busca_sdk(dado):
    """La carpeta bin del SDK de Windows con makeappx y signtool. La más nueva que haya."""
    if dado:
        return Path(dado)
    base = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Windows Kits' / '10' / 'bin'
    if not base.is_dir():
        sys.exit('no encuentro el SDK de Windows: pasa --sdk con la carpeta que tiene makeappx.exe')
    candidatas = sorted((d / 'x64' for d in base.glob('10.*') if (d / 'x64' / 'makeappx.exe').is_file()),
                        key=lambda d: [int(x) for x in d.parent.name.split('.')])
    if not candidatas:
        sys.exit('no encuentro makeappx.exe bajo %s: pasa --sdk' % base)
    return candidatas[-1]


def sujeto_del_certificado(huella):
    """El CN del certificado, o None si no se pudo leer. Solo para avisar antes de firmar."""
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "(Get-ChildItem -LiteralPath 'Cert:\\CurrentUser\\My\\%s').Subject" % huella],
            capture_output=True, text=True, errors='replace', timeout=30)
        salida = (r.stdout or '').strip()
        return salida or None
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    p = argparse.ArgumentParser(description='Arma y firma el .msix del port UWP de Diddy Kong Racing.')
    p.add_argument('--version', required=True, help='versión del paquete, cuatro números (p. ej. 0.1.1.3)')
    p.add_argument('--exe', required=True, help='mdkr64.exe salido de build_uwp.py')
    p.add_argument('--rom', required=True, help='tu ROM de Diddy Kong Racing, revisión 1.1 («Rev A»)')
    p.add_argument('--dawn-bin', required=True, help='carpeta bin de uwp-dep/x64 (las cuatro DLL de Dawn)')
    p.add_argument('--sdl2-bin', required=True, help='carpeta con la SDL2.dll compilada para WinRT')
    p.add_argument('--assets', required=True, help='carpeta con tus nueve mosaicos (make_tiles.py)')
    p.add_argument('--salida', required=True, help='dónde dejar el .msix')
    p.add_argument('--certificado', required=True, help='huella SHA-1 de TU certificado en Cert:\\CurrentUser\\My')
    p.add_argument('--sdk', help='carpeta bin del SDK de Windows (por omisión, la más nueva instalada)')
    a = p.parse_args()

    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', a.version):
        sys.exit('la versión son cuatro números separados por puntos (p. ej. 0.1.1.3), no %r' % a.version)

    exe, rom = Path(a.exe), Path(a.rom)
    dawn_bin, sdl2_bin = Path(a.dawn_bin), Path(a.sdl2_bin)
    assets, salida = Path(a.assets), Path(a.salida)
    sdk = busca_sdk(a.sdk)

    dlls = {n: dawn_bin / n for n in DLLS_DAWN}
    dlls.update({n: sdl2_bin / n for n in DLLS_SDL2})

    faltan = [str(x) for x in [exe, rom, MANIFIESTO, sdk / 'makeappx.exe', sdk / 'signtool.exe']
              if not x.exists()]
    faltan += [str(v) for v in dlls.values() if not v.exists()]
    faltan += [str(assets / m) for m in MOSAICOS if not (assets / m).is_file()]
    if faltan:
        print('=== falta material ===')
        for f in faltan:
            print('  %s' % f)
        print('\n  Los mosaicos los produce tools/make_tiles.py a partir de tu arte (docs/ASSETS.md).')
        return 2

    manifiesto = MANIFIESTO.read_text(encoding='utf-8')
    if VERSION_PLANTILLA not in manifiesto:
        sys.exit('la plantilla del manifiesto ya no dice Version="%s": el reemplazo de versión no '
                 'ocurriría y el paquete saldría con la versión equivocada sin avisar.' % VERSION_PLANTILLA)

    if 'CHANGE-ME' in manifiesto:
        sys.exit('package/Package.appxmanifest sigue con los CHANGE-ME de la plantilla.\n'
                 'Pon tu Publisher (el CN de tu certificado) y el Name que quieras para el\n'
                 'paquete antes de empaquetar: docs/INSTALL.es.md §3.')

    # Aviso temprano: si el CN del certificado no es el Publisher del manifiesto, la consola
    # rechaza el paquete. Mejor decirlo ahora que después de empaquetar 28 MB.
    m = re.search(r'Publisher="([^"]+)"', manifiesto)
    if m:
        sujeto = sujeto_del_certificado(a.certificado)
        if sujeto and sujeto != m.group(1):
            sys.exit('el Publisher del manifiesto (%s) no es el del certificado (%s): la consola\n'
                     'rechazaría el paquete. Pon TU CN en package/Package.appxmanifest.'
                     % (m.group(1), sujeto))

    h = sha256(rom)
    if h != ROM_SHA256:
        print('=== la ROM no es la revisión us.v80 (1.1, «Rev A») ===')
        print('  sha256 leído    : %s' % h)
        print('  sha256 esperado : %s' % ROM_SHA256)
        print('\n  La revisión 1.0 no vale: el port la rechaza. En los sets habituales, la buena')
        print('  aparece como «(Rev A)».')
        return 2
    print('  ROM verificada: us.v80 (%.0f MB)' % (rom.stat().st_size / 1048576))

    salida.mkdir(parents=True, exist_ok=True)
    raiz = salida / 'contenido'
    if raiz.exists():
        shutil.rmtree(raiz)          # carpeta de trabajo propia y regenerable
    raiz.mkdir(parents=True)

    shutil.copy2(exe, raiz / 'mdkr64.exe')
    for nombre, origen in dlls.items():
        shutil.copy2(origen, raiz / nombre)
    shutil.copy2(rom, raiz / ROM_EN_PAQUETE)
    (raiz / 'Assets').mkdir()
    for mosaico in MOSAICOS:
        shutil.copy2(assets / mosaico, raiz / 'Assets' / mosaico)

    (raiz / 'AppxManifest.xml').write_text(
        manifiesto.replace('Version="%s"' % VERSION_PLANTILLA, 'Version="%s"' % a.version),
        encoding='utf-8')

    archivos = [x for x in raiz.rglob('*') if x.is_file()]
    print('  contenido: %d archivos, %.1f MB'
          % (len(archivos), sum(x.stat().st_size for x in archivos) / 1048576))

    msix = salida / ('DiddyKongRacing_%s_x64.msix' % a.version)
    if msix.exists():
        msix.unlink()
    r = subprocess.run([str(sdk / 'makeappx.exe'), 'pack', '/o', '/d', str(raiz), '/p', str(msix)],
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        print('=== makeappx ===')
        print(r.stdout[-2500:])
        print(r.stderr[-1500:])
        return r.returncode

    r = subprocess.run([str(sdk / 'signtool.exe'), 'sign', '/fd', 'SHA256',
                        '/sha1', a.certificado, '/s', 'My', str(msix)],
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        print('=== signtool ===')
        print(r.stdout[-1500:])
        print(r.stderr[-1000:])
        return r.returncode

    print('  FIRMADO: %s  (%.1f MB)' % (msix.name, msix.stat().st_size / 1048576))
    print('  sha256 : %s' % sha256(msix))
    print('  %s' % msix)
    print('\n  Instalarlo en la consola: docs/INSTALL.es.md §7.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
