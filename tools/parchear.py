# -*- coding: utf-8 -*-
"""Lo que comparten los patch_*.py: leer, comprobar, sustituir y escribir.

Cada parche de esta carpeta hace lo mismo con anclas distintas, asi que la mecanica vive aqui una
sola vez:

    import parchear

    TEMA = 'de que va este parche'
    CAMBIOS = [(archivo_relativo, texto_viejo, texto_nuevo), ...]

    def main():
        parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                         hecho='que se consiguio')

Las tres reglas que cumple todo parche de este repositorio, y que son el motivo de que
apply_uwp.py pueda detenerse a medias sin dejar un arbol inservible:

- **Todo o nada, y para el parche entero.** Las sustituciones de TODOS los archivos se calculan
  en memoria, y no se escribe ninguno hasta que todas cuadran. Cada ancla tiene que aparecer
  exactamente una vez; si una sola no cuadra, no se escribe nada en ninguna parte y el script
  muere diciendo cual, en que archivo y cuantas veces la encontro.

- **Idempotente, y sin marca inyectada.** «Ya aplicado» se decide preguntando si el texto NUEVO ya
  esta en el archivo, no por un comentario centinela. Es la version honesta: la marca habria que
  meterla dentro del arbol del juego, que no es nuestro, y tendria que viajar en el texto exacto
  que el port ya tiene compilado y validado. Asi, lo que se escribe es exactamente lo que el
  arbol que corre tiene, y la comprobacion no depende de que nadie retoque un comentario.

- **Escritura atomica y sin tocar el formato.** Se escribe un .tmp al lado y se reemplaza de una
  vez, conservando los finales de linea que el archivo ya tenia. Golden Balloon tiene archivos con
  CRLF y archivos con LF, y .gitattributes se encarga de ellos: cambiarlos aqui ensuciaria el
  `git status` del arbol del juego con archivos que el parche no toco.

Los textos que los parches escriben DENTRO del arbol del juego son, caracter por caracter, los que
tiene el arbol con el que se construyo y probo el port en la consola.

Van en castellano y, salvo algun entrecomillado, sin acentos: es como se escribieron. El arbol de
Golden Balloon es UTF-8 y ya lleva caracteres anchos por su cuenta --1449 rayas, entre otros, en
228 archivos--, asi que no hay una regla de ASCII puro que respetar aqui; lo que si conviene
recordar es que esto solo se compila con clang, que supone UTF-8, y que MSVC leeria un archivo sin
BOM con la pagina de codigos del sistema. Los comentarios de los scripts llevan acentos, porque
solo los lee Python.
"""
import os
import sys

__all__ = ['raiz', 'leer', 'escribir', 'aplicar_varios', 'informe']

# Dos archivos que tiene toda raiz de Golden Balloon y ningun otro arbol: sirven de comprobacion
# barata de que el argumento apunta a donde debe.
SENAS = ('CMakeLists.txt', os.path.join('platform', 'main_pc.c'))


def raiz(ayuda='<ruta de la raiz del arbol de Golden Balloon>'):
    """La raíz del árbol del juego, tomada del primer argumento que no sea una opción."""
    libres = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not libres:
        sys.exit('uso: %s %s' % (os.path.basename(sys.argv[0]), ayuda))
    return comprueba(libres[0])


def comprueba(ruta):
    """Aborta si no parece la raíz de Golden Balloon. Devuelve la ruta absoluta."""
    ruta = os.path.abspath(ruta)
    for sena in SENAS:
        if not os.path.isfile(os.path.join(ruta, sena)):
            sys.exit('no parece la raíz del árbol de Golden Balloon (falta %s): %s' % (sena, ruta))
    return ruta


def leer(ruta):
    """Devuelve (texto con '\\n', final de línea original)."""
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8', errors='replace')
    return crudo.replace('\r\n', '\n'), ('\r\n' if '\r\n' in crudo else '\n')


def escribir(ruta, texto, eol):
    """Escribe de una vez: un .tmp al lado y un reemplazo atómico."""
    tmp = ruta + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(texto.replace('\n', eol))
    os.replace(tmp, ruta)


def aplicar_varios(raiz_juego, cambios, tema):
    """Aplica los cambios, agrupados por archivo. Devuelve la lista de archivos escritos.

    `cambios` es una lista de tríos (archivo relativo a la raíz, texto viejo, texto nuevo). Para
    cada trío:

      - si el texto nuevo ya está, ese cambio estaba hecho y se salta;
      - si no, el viejo tiene que aparecer exactamente una vez;
      - si no aparece ninguno de los dos, el árbol no es el que este parche espera y se aborta.

    Nada se escribe hasta que todos los cambios de ese archivo cuadran.
    """
    por_archivo = {}
    for rel, viejo, nuevo in cambios:
        por_archivo.setdefault(rel, []).append((viejo, nuevo))

    # Primero se calcula TODO en memoria. Solo si los cambios de todos los archivos cuadran se
    # escribe alguno: así un parche que toca cinco archivos y tropieza en el cuarto no deja los
    # tres primeros escritos y el árbol a medio camino entre dos versiones.
    pendientes = []
    for rel, lista in por_archivo.items():
        ruta = os.path.join(raiz_juego, rel.replace('/', os.sep))
        if not os.path.isfile(ruta):
            sys.exit('%s: no existe en el árbol (%s)' % (rel, tema))
        texto, eol = leer(ruta)
        original = texto
        for n, (viejo, nuevo) in enumerate(lista, 1):
            if nuevo in texto:
                continue                      # ese cambio ya estaba
            veces = texto.count(viejo)
            if veces != 1:
                sys.exit('%s (cambio %d de %d, %s): el ancla aparece %d veces, se esperaba 1.\n'
                         '  El árbol no es el que este parche espera: ¿es Golden Balloon v1.7.0?\n'
                         '  No se ha escrito nada.\n'
                         '  Ancla: %r' % (rel, n, len(lista), tema, veces, viejo[:70]))
            texto = texto.replace(viejo, nuevo, 1)
        if texto != original:
            pendientes.append((ruta, texto, eol, rel))

    for ruta, texto, eol, _ in pendientes:
        escribir(ruta, texto, eol)
    return [rel for _, _, _, rel in pendientes]


def informe(*escritos, hecho=None, nada='ya estaba aplicado'):
    """Imprime qué archivos se tocaron y para qué, o que no hubo nada que hacer."""
    tocados = [e for e in escritos if e]
    if not tocados:
        print('  %s' % nada)
        return
    print('  %s' % (hecho or ', '.join(tocados)))
    for t in sorted(tocados):
        print('      %s' % t)
