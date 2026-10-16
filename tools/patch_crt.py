# -*- coding: utf-8 -*-
"""Los dos choques con el CRT estricto de UWP: el setvbuf que mata el arranque y el sprintf del decomp.

Los dos son fallos latentes del port de escritorio que solo el CRT de la tienda delata, y los dos
se arreglan sin esconder nada tras un #ifdef que solo valga en consola.

--- 1. setvbuf, en main_pc.c ------------------------------------------------------------------

El juego instalaba bien, aparecia en la lista de la consola con su icono... y al lanzarlo se
cerraba al instante. El volcado de la Xbox lo senalo sin ambiguedad:

    SDL2!SDL_WinRTApp::Run          <- SDL ya tenia el CoreWindow y llamo a nuestro main
      mdkr64+0x442dad
        mdkr64+0x11a5ed
          ucrtbase!setvbuf
            ucrtbase!invoke_watson  -> c0000409, subcodigo 5 = FAST_FAIL_INVALID_ARG

Y no era un problema de UWP. El contrato de setvbuf exige, cuando el modo es _IOLBF o _IOFBF, un
tamano entre 2 e INT_MAX. main_pc.c pasaba CERO. MinGW se lo traga; UCRT lo cuenta como parametro
invalido y, dentro de un AppContainer, el manejador por defecto no devuelve el control: hace
fast-fail. De ahi la muerte instantanea y sin rastro.

En escritorio queda la intencion declarada (salida por lineas) con un tamano valido. En consola la
salida no va a un terminal sino a un archivo de registro, y el CRT de Windows trata _IOLBF como
_IOFBF -- «por lineas» alli no significa nada --, asi que va sin buffer: lo ultimo que se escribio
sobrevive a una caida, que es justo cuando hace falta leerlo.

--- 2. sprintf, en printf.c -------------------------------------------------------------------

El juego define su propio sprintf. Con MinGW convivia con el del CRT, porque aquel vive en una
biblioteca y el enlazador solo lo saca si nadie mas lo define. UCRT no funciona asi: su stdio.h
EMITE una copia en linea en cada unidad, de modo que la definicion fuerte del juego choca de
frente y el enlace se cae.

El primer intento fue devolver a UCRT al modelo de biblioteca (-D_NO_CRT_STDIO_INLINE mas
legacy_stdio_definitions.lib). Fallo por una razon medida: esa biblioteca es UN SOLO objeto, asi
que sacar printf arrastra tambien sprintf y el choque vuelve.

La salida buena la da el propio codigo: ese sprintf NO TIENE NI UN LLAMADOR en todo el arbol --
los tres sitios que lo nombran son comentarios sobre este mismo asunto -- y objects.c lo dice con
todas las letras, «the game's own sprintf() is the N64 implementation and is not usable for host
diagnostics». La ruta de spacing codes tampoco pasa por ahi: va directa a DKR_VSPRINTF. Asi que en
UWP se queda fuera del binario y manda el del CRT.

Idempotente y todo o nada; escritura atomica. Lo aplica tools/apply_uwp.py, que es el
punto de entrada: este script se puede correr solo, pero el orden y los requisitos los
comprueba aquel.

Uso: patch_crt.py <raiz del arbol de Golden Balloon>
"""
import parchear

TEMA = 'dkr-xbox: strict CRT'

# Cada trío: archivo relativo a la raíz del árbol, texto que se busca, texto que queda.
CAMBIOS = [
  # --- platform/main_pc.c (hunk 1) ---
  ('platform/main_pc.c',
   # busca:
   ('    setvbuf(stdout, NULL, _IOLBF, 0);\n'
    '    setvbuf(stderr, NULL, _IOLBF, 0);'),
   # queda:
   ('    /* El tamano NO puede ser 0 con _IOLBF: el contrato de setvbuf pide entre 2 e INT_MAX cuando\n'
    '     * el modo es por lineas o por bloques. MinGW lo tolera; UCRT lo cuenta como parametro\n'
    '     * invalido y, dentro de un AppContainer, el manejador por defecto no devuelve el control:\n'
    '     * hace fast-fail (0xC0000409, FAST_FAIL_INVALID_ARG) y la aplicacion muere en el arranque\n'
    '     * sin dejar nada en pantalla. Costo un volcado de la consola encontrarlo. */\n'
    '#if defined(MDKR_UWP)\n'
    '    /* En consola la salida no va a un terminal sino a un archivo de registro, y el CRT de Windows\n'
    '     * trata _IOLBF como _IOFBF -- «por lineas» alli no significa nada. Sin buffer, para que lo\n'
    '     * ultimo que se escribio sobreviva a una caida, que es justo cuando hace falta leerlo. */\n'
    '    setvbuf(stdout, NULL, _IONBF, 0);\n'
    '    setvbuf(stderr, NULL, _IONBF, 0);\n'
    '#else\n'
    '    setvbuf(stdout, NULL, _IOLBF, BUFSIZ);\n'
    '    setvbuf(stderr, NULL, _IOLBF, BUFSIZ);\n'
    '#endif')),
  # --- game/src/printf.c (hunk 1) ---
  ('game/src/printf.c',
   # busca:
   ('UNUSED int sprintf(char *s, const char *format, ...) {\n'
    '    va_list arg;\n'
    '    int done;\n'
    '\n'
    '    va_start(arg, format);\n'
    '    done = DKR_VSPRINTF(s, format, arg);\n'
    '    va_end(arg);\n'
    '\n'
    '    return done;\n'
    '}'),
   # queda:
   ('#if !defined(MDKR_UWP)\n'
    '/* En UWP esta definicion se queda fuera del binario, y no es una renuncia: no tiene un\n'
    ' * solo llamador en todo el arbol (los tres sitios que nombran sprintf son comentarios\n'
    ' * sobre este mismo choque) y objects.c ya lo dice con todas las letras -- «the game\'s own\n'
    ' * sprintf() is the N64 implementation and is not usable for host diagnostics». La ruta de\n'
    ' * spacing codes tampoco pasa por aqui: va directa a DKR_VSPRINTF.\n'
    ' *\n'
    ' * Con MinGW convivia con el del CRT porque aquel vive en una biblioteca y solo se saca si\n'
    ' * nadie mas lo define. UCRT emite una copia en linea en cada unidad, asi que esta\n'
    ' * definicion fuerte choca de frente y el enlace se cae. */\n'
    'UNUSED int sprintf(char *s, const char *format, ...) {\n'
    '    va_list arg;\n'
    '    int done;\n'
    '\n'
    '    va_start(arg, format);\n'
    '    done = DKR_VSPRINTF(s, format, arg);\n'
    '    va_end(arg);\n'
    '\n'
    '    return done;\n'
    '}\n'
    '#endif /* !MDKR_UWP */')),
]


def main():
    parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                     hecho='main_pc.c: setvbuf con tamano valido; printf.c: el sprintf del decomp fuera del binario UWP')


if __name__ == '__main__':
    main()
