# -*- coding: utf-8 -*-
"""Genera los nueve mosaicos del paquete UWP a partir de TUS cuatro imágenes.

Este repositorio no trae ningún mosaico: los del port real están hechos con la carátula del
juego, que no es nuestra. Pones las tuyas y esto arma las nueve que el manifiesto nombra.

Cuatro se copian tal cual, porque ya tienen la medida exacta:

    xbox-sq1.png (150x150)  -> Square150x150Logo.png
    xbox-sq2.png (300x300)  -> Square150x150Logo.scale-200.png
    xbox-ss1.png (620x300)  -> SplashScreen.png
    xbox-ss2.png (1240x600) -> SplashScreen.scale-200.png

Las otras cinco se derivan de la cuadrada grande (xbox-sq2) reduciendo con LANCZOS, porque el
manifiesto las exige y nadie quiere dibujar un icono de 24 píxeles a mano:

    Square44x44Logo (44, 88 y 24)  el icono pequeño de las listas de aplicaciones
    StoreLogo (50 y 100)           el que pide <Properties><Logo>

Dos cosas que no son obvias:

  - **No se declara mosaico ancho** (Wide310x150Logo). En modo desarrollador la consola no lo
    muestra nunca, así que el manifiesto no lo nombra y aquí no se genera.
  - **Los nombres SIN calificador de escala tienen que existir igual.** El paquete se arma sin
    resources.pri, y entonces makeappx busca literalmente el nombre que dice el manifiesto.

Medidas y criterios de arte: docs/ASSETS.md.

Uso:
    python tools/make_tiles.py --origen <carpeta con tus 4 PNG> --salida <carpeta de mosaicos>

Necesita Pillow:  pip install pillow

Recompilaciones — https://github.com/jajdp/dkr-xbox
MIT (ver LICENSE)
"""
import argparse
import shutil
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    if hasattr(flujo, 'reconfigure'):
        flujo.reconfigure(encoding='utf-8', errors='replace')

try:
    from PIL import Image
except ImportError:
    sys.exit('falta Pillow: pip install pillow')

# copia directa: tu imagen ya tiene la medida exacta
DIRECTOS = {
    'xbox-sq1.png': ('Square150x150Logo.png', (150, 150)),
    'xbox-sq2.png': ('Square150x150Logo.scale-200.png', (300, 300)),
    'xbox-ss1.png': ('SplashScreen.png', (620, 300)),
    'xbox-ss2.png': ('SplashScreen.scale-200.png', (1240, 600)),
}

# derivados de la cuadrada grande
DERIVADOS = {
    'Square44x44Logo.png': 44,
    'Square44x44Logo.scale-200.png': 88,
    'Square44x44Logo.targetsize-24_altform-unplated.png': 24,
    'StoreLogo.png': 50,
    'StoreLogo.scale-200.png': 100,
}

GRANDE = 'xbox-sq2.png'


def main():
    p = argparse.ArgumentParser(description='Genera los mosaicos del paquete UWP a partir de tu arte.')
    p.add_argument('--origen', required=True, help='carpeta con xbox-sq1/sq2/ss1/ss2.png')
    p.add_argument('--salida', required=True, help='carpeta donde dejar los nueve mosaicos')
    a = p.parse_args()

    origen, salida = Path(a.origen), Path(a.salida)
    if not origen.is_dir():
        sys.exit('no existe la carpeta de origen: %s' % origen)
    salida.mkdir(parents=True, exist_ok=True)
    problemas = []

    for nombre, (destino, medida) in DIRECTOS.items():
        f = origen / nombre
        if not f.is_file():
            problemas.append('falta %s (%dx%d)' % (nombre, medida[0], medida[1]))
            continue
        with Image.open(f) as im:
            if im.size != medida:
                problemas.append('%s mide %dx%d, se esperaba %dx%d'
                                 % (nombre, im.size[0], im.size[1], medida[0], medida[1]))
                continue
        shutil.copy2(f, salida / destino)
        print('  %-14s -> %-46s %dx%d' % (nombre, destino, medida[0], medida[1]))

    grande = origen / GRANDE
    if grande.is_file():
        with Image.open(grande) as im:
            base = im.convert('RGBA')
            for destino, lado in DERIVADOS.items():
                base.resize((lado, lado), Image.LANCZOS).save(salida / destino)
                print('  (derivado)     -> %-46s %dx%d' % (destino, lado, lado))
    else:
        problemas.append('falta %s, del que salen los iconos pequeños' % GRANDE)

    print()
    if problemas:
        print('=== PROBLEMAS ===')
        for x in problemas:
            print('  %s' % x)
        print('\n  Medidas y criterios de arte: docs/ASSETS.md')
        return 1
    print('  %d mosaicos en %s' % (len(list(salida.glob('*.png'))), salida))
    return 0


if __name__ == '__main__':
    sys.exit(main())
