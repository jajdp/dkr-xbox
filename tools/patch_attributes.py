# -*- coding: utf-8 -*-
"""Arregla el guard que anulaba EN SILENCIO todos los __attribute__ del arbol.

game/include/PRinternal/macros.h trae, para compiladores que no entienden los atributos de GCC:

    #ifndef __GNUC__
    #define __attribute__(x)
    #endif

Clang SI los entiende, pero cuando apunta a --target=x86_64-pc-windows-msvc emula los
predefinidos de MSVC y NO define __GNUC__. Asi que el guard se activaba y vaciaba todos los
atributos del juego en la build UWP, sin un solo aviso.

Lo que se perdia, y lo que costo encontrarlo: UN __attribute__((constructor)),
mdkr64_fill_math_tables, que rellena gSineTable y gArcTanTable desde las tablas horneadas y fija
la semilla del RNG. Sin el, toda la trigonometria devuelve 0: las matrices de rotacion degeneran,
los modelos 3D colapsan y DESAPARECEN -- mientras el texto 2D, que no rota, sigue dibujandose. El
sintoma era exactamente ese: en la introduccion salian los nombres de los corredores y no los
corredores. Y la semilla sin fijar explica de paso que el RNG diera 2274 tiradas donde el PC daba
4273 y que el hash de simulacion se separase en el tick 89.

Caian tambien 6 destructores, 3 aligned, 3 weak, 3 optimize, 2 noreturn, 2 format y 2 unused.

El arreglo es de una linea y no cambia nada en escritorio: clang define __clang__ apunte a donde
apunte, asi que basta con nombrarlo junto a __GNUC__.

Idempotente y todo o nada; escritura atomica. Lo aplica tools/apply_uwp.py, que es el
punto de entrada: este script se puede correr solo, pero el orden y los requisitos los
comprueba aquel.

Uso: patch_attributes.py <raiz del arbol de Golden Balloon>
"""
import parchear

TEMA = 'dkr-xbox: __attribute__ under clang/MSVC'

# Cada trío: archivo relativo a la raíz del árbol, texto que se busca, texto que queda.
CAMBIOS = [
  # --- game/include/PRinternal/macros.h (hunk 1) ---
  ('game/include/PRinternal/macros.h',
   # busca:
   ('#ifndef __GNUC__'),
   # queda:
   ('/* Clang entiende los atributos de GCC apunte a donde apunte, pero cuando emula a MSVC\n'
    ' * (--target=x86_64-pc-windows-msvc, que es lo que exige UWP) NO define __GNUC__: imita los\n'
    ' * predefinidos de MSVC. Sin nombrar tambien a __clang__, este guard anulaba EN SILENCIO todos\n'
    ' * los atributos del arbol en esa build -- incluido el unico __attribute__((constructor)), el que\n'
    ' * rellena gSineTable y fija la semilla del RNG. El resultado era trigonometria que devolvia 0 y\n'
    ' * modelos 3D invisibles en la consola. */\n'
    '#if !defined(__GNUC__) && !defined(__clang__)')),
]


def main():
    parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                     hecho='macros.h: los atributos tambien valen con clang apuntando a MSVC')


if __name__ == '__main__':
    main()
