# -*- coding: utf-8 -*-
"""Hace portable el layout del display list entre el empaquetado de GCC y el de MSVC.

El port de escritorio compila con -mno-ms-bitfields, y clang lo RECHAZA cuando apunta al ABI de
MSVC -- que es el unico que la Xbox acepta dentro de un AppContainer. Quitar la bandera sin mas
cambia la forma de las estructuras del display list, y eso no es cosmetico: medio juego avanza por
el display list en saltos de 8 bytes, asi que si la union Gfx pasa a medir 16 no hay pantalla de
titulo, hay basura.

El volcado de layouts (-fdump-record-layouts, bajo las dos reglas de empaquetado) demostro que de
26 estructuras solo DOS cambian de forma, y que son estas dos las que arrastran a Gfx. La regla de
MSVC que muerde es una sola: un campo de bits seguido de un tipo de OTRO tamano abre una palabra
nueva; GCC los mete en la misma. Asi que basta con igualar los tipos:

  Gpopmtx  : `unsigned char param:8` -> `unsigned int param:8`   (el tipo de su vecino pad2)
  Gsetcolor: `int cmd:8`             -> `unsigned char cmd:8`    (el tamano de sus vecinos pad)

Las dos son NEUTRAS bajo GCC -- el volcado lo confirma campo a campo despues de aplicarlas --, y
van guardadas con NATIVE_PORT igual que el arreglo de `color` que ya vivia en Gsetcolor, para que
la compilacion original de N64 siga saliendo byte a byte igual.

Idempotente y todo o nada; escritura atomica. Lo aplica tools/apply_uwp.py, que es el
punto de entrada: este script se puede correr solo, pero el orden y los requisitos los
comprueba aquel.

Uso: patch_display_list.py <raiz del arbol de Golden Balloon>
"""
import parchear

TEMA = 'dkr-xbox: portable bitfield layout'

# Cada trío: archivo relativo a la raíz del árbol, texto que se busca, texto que queda.
CAMBIOS = [
  # --- game/include/PR/gbi.h (hunk 1) ---
  ('game/include/PR/gbi.h',
   # busca:
   ('\t\tunsigned char\tparam:8;'),
   # queda:
   ('#if defined(NATIVE_PORT)\n'
    '\t/* Portabilidad del empaquetado (misma familia que el arreglo de `color` en Gsetcolor):\n'
    '\t * MSVC abre una palabra nueva cuando un campo de bits va seguido de otro de tipo de\n'
    '\t * distinto tamano, asi que `unsigned char param:8` detras de `int pad2:24` empujaba este\n'
    '\t * paquete de 8 a 12 bytes y la union Gfx de 8 a 16. Declararlo del mismo tamano que su\n'
    '\t * vecino lo devuelve al byte 7 en los DOS compiladores; bajo GCC no mueve nada (verificado\n'
    '\t * con -fdump-record-layouts). */\n'
    '\t\tunsigned int\tparam:8;\n'
    '#else\n'
    '\t\tunsigned char\tparam:8;\n'
    '#endif')),
  # --- game/include/PR/gbi.h (hunk 2) ---
  ('game/include/PR/gbi.h',
   # busca:
   ('typedef struct {\n'
    '\t\tint\t\tcmd:8;\n'
    '\t\tunsigned char\tpad;'),
   # queda:
   ('typedef struct {\n'
    '#if defined(NATIVE_PORT)\n'
    '\t/* Mismo motivo que en Gpopmtx: con ABI de MSVC un campo de bits `int` reserva 4 bytes\n'
    '\t * enteros, asi que los tres `unsigned char` de detras empezaban en el byte 4 y el paquete\n'
    '\t * pasaba de 8 a 12. Declarando el campo de bits del tamano de sus vecinos, `pad` vuelve al\n'
    '\t * byte 1 en los dos compiladores. Bajo GCC el layout no cambia. */\n'
    '\t\tunsigned char\tcmd:8;\n'
    '#else\n'
    '\t\tint\t\tcmd:8;\n'
    '#endif\n'
    '\t\tunsigned char\tpad;')),
]


def main():
    parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                     hecho='gbi.h: Gpopmtx y Gsetcolor con los campos de bits igualados a sus vecinos')


if __name__ == '__main__':
    main()
