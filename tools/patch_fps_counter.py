# -*- coding: utf-8 -*-
"""Contador de FPS en pantalla, que R3 enciende y apaga.

En la consola no hay teclado ni ventana con titulo, asi que el contador tiene que dibujarse DENTRO
del juego y conmutarse con el mando. Cinco archivos, y cada uno por una razon:

  enh_speedometer.c   el contador y su medicion. Vive aqui, y no en un archivo propio, porque la
                      build UWP toma las unidades de compilacion de las ordenes que ya emite
                      CMake: una unidad nueva obligaria a regenerar el proyecto. Y es el archivo
                      que ya sabe dibujar texto del port sobre el HUD, asi que el contador sale
                      con la misma fuente y la misma sombra que el velocimetro
  enh_speedometer.h   la bandera y la funcion, declaradas
  game_ui.c           uno de los dos puntos de dibujado por cuadro: el HUD de carrera
  menu.c              el otro: menu_loop. Al final, ya dibujado el menu, para que nada lo tape
  platform_sdl_min.c  R3. Se MIRA el boton, no se consume: si el jugador lo tiene asignado a una
                      accion del juego, la sigue haciendo

⚠ Se miden las PRESENTACIONES (g_frameCounter), no las llamadas a la funcion de dibujado: eso
ultimo daria los ticks del juego -- 30/s -- y seguiria diciendo 30 con la presentacion suave
encendida, que es justo lo que el contador tiene que poder desmentir. La medida sigue corriendo con
el contador oculto, para que al encenderlo ya haya un valor fresco.

Arriba a la derecha: la esquina que el juego deja libre en carrera (los contadores de platanos y de
vueltas van arriba a la IZQUIERDA) y tambien en los menus. En consola arranca encendido.

Idempotente y todo o nada; escritura atomica. Lo aplica tools/apply_uwp.py, que es el
punto de entrada: este script se puede correr solo, pero el orden y los requisitos los
comprueba aquel.

Uso: patch_fps_counter.py <raiz del arbol de Golden Balloon>
"""
import parchear

TEMA = 'dkr-xbox: on-screen FPS counter'

# Cada trío: archivo relativo a la raíz del árbol, texto que se busca, texto que queda.
CAMBIOS = [
  # --- platform/enh_speedometer.c (hunk 1) ---
  ('platform/enh_speedometer.c',
   # busca:
   ('#include <stdlib.h>\n'
    ''),
   # queda:
   ('#include <stdlib.h>\n'
    '#include <time.h>   /* el contador de FPS: el port no expone reloj de pared */\n'
    '')),
  # --- platform/enh_speedometer.c (hunk 2) ---
  ('platform/enh_speedometer.c',
   # busca:
   ('\n'
    'void mdkr_enh_speedometer_draw(Gfx **displayList) {'),
   # queda:
   ('\n'
    '/* Contador de FPS con R3.\n'
    ' *\n'
    ' * Vive aqui, y no en un archivo propio, porque el build UWP toma las unidades de compilacion de\n'
    ' * las ordenes que ya emite CMake: una unidad nueva obligaria a regenerar el proyecto. Este\n'
    ' * archivo es ademas el que ya sabe dibujar texto del port sobre el HUD, asi que el contador sale\n'
    ' * con la misma fuente y la misma sombra que el velocimetro.\n'
    ' *\n'
    ' * En la consola arranca encendido; R3 lo apaga y lo enciende (platform/platform_sdl_min.c). */\n'
    '#ifdef MDKR_UWP\n'
    'int g_mdkr_mostrar_fps = 1;   /* en consola, encendido de fabrica */\n'
    '#else\n'
    'int g_mdkr_mostrar_fps = 0;\n'
    '#endif\n'
    '\n'
    '/* Arriba a la derecha: la esquina que el juego deja libre en carrera (los contadores de platanos\n'
    ' * y vueltas van arriba a la IZQUIERDA) y tambien en los menus. */\n'
    '#define FPS_X (SCREEN_WIDTH - 10)\n'
    '#define FPS_Y 8\n'
    '\n'
    'void mdkr_enh_fps_draw(Gfx **displayList) {\n'
    '    static time_t ventana = 0;\n'
    '    static int base = 0;\n'
    '    static int medida = -1;\n'
    '    char text[16];\n'
    '    const time_t ahora = time(NULL);\n'
    '\n'
    '    if (displayList == NULL) {\n'
    '        return;\n'
    '    }\n'
    '\n'
    '    /* Se miden las PRESENTACIONES (g_frameCounter), no las veces que se llama a esta funcion:\n'
    '     * eso ultimo daria los ticks del juego, 30/s, y seguiria diciendo 30 con la presentacion\n'
    '     * suave encendida. La medida sigue corriendo con el contador oculto, para que al encenderlo\n'
    '     * ya haya un valor fresco. Se publica al cambiar el segundo. */\n'
    '    if (ventana == 0) {\n'
    '        ventana = ahora;\n'
    '        base = g_frameCounter;\n'
    '    }\n'
    '    if (ahora != ventana) {\n'
    '        medida = (int)((double)(g_frameCounter - base) / (double)(ahora - ventana) + 0.5);\n'
    '        ventana = ahora;\n'
    '        base = g_frameCounter;\n'
    '    }\n'
    '    if (!g_mdkr_mostrar_fps || medida < 0) {\n'
    '        return;\n'
    '    }\n'
    '    sprintf(text, "%d FPS", medida);\n'
    '\n'
    '    /* Misma sombra de dos pasadas que el velocimetro, para que se lea sobre cualquier fondo. */\n'
    '    set_text_font(ASSET_FONTS_FUNFONT);\n'
    '    set_text_background_colour(0, 0, 0, 0);\n'
    '    set_text_colour(0, 0, 0, 255, 180);\n'
    '    draw_text(displayList, FPS_X + 1, FPS_Y + 1, text, ALIGN_TOP_RIGHT);\n'
    '    set_text_colour(255, 255, 255, 0, 235);\n'
    '    draw_text(displayList, FPS_X, FPS_Y, text, ALIGN_TOP_RIGHT);\n'
    '\n'
    '    /* Igual que el velocimetro: devolver el color primitivo a su valor por defecto, para que\n'
    '     * nada de lo que se dibuje despues herede la opacidad del rotulo. */\n'
    '    rendermode_reset(displayList);\n'
    '    gDPSetPrimColor((*displayList)++, 0, 0, 255, 255, 255, 255);\n'
    '}\n'
    '\n'
    'void mdkr_enh_speedometer_draw(Gfx **displayList) {')),
  # --- platform/enh_speedometer.h (hunk 1) ---
  ('platform/enh_speedometer.h',
   # busca:
   ('void mdkr_enh_speedometer_draw(Gfx **displayList);\n'
    '\n'
    '#ifdef __cplusplus\n'
    '}'),
   # queda:
   ('void mdkr_enh_speedometer_draw(Gfx **displayList);\n'
    '\n'
    '/* Contador de FPS con R3. Lo conmuta platform_sdl_min.c; lo dibujan los dos puntos por\n'
    ' * cuadro que tiene el juego: el HUD de carrera (game_ui.c) y menu_loop (menu.c). */\n'
    'extern int g_mdkr_mostrar_fps;\n'
    'void mdkr_enh_fps_draw(Gfx **displayList);\n'
    '\n'
    '#ifdef __cplusplus\n'
    '}')),
  # --- game/src/game_ui.c (hunk 1) ---
  ('game/src/game_ui.c',
   # busca:
   ('                mdkr_enh_speedometer_draw(&gHudDL);\n'
    '#endif'),
   # queda:
   ('                mdkr_enh_speedometer_draw(&gHudDL);\n'
    '                /* Contador de FPS con R3: detras del velocimetro, por lo mismo que el. */\n'
    '                mdkr_enh_fps_draw(&gHudDL);\n'
    '#endif')),
  # --- game/src/menu.c (hunk 1) ---
  ('game/src/menu.c',
   # busca:
   ('#ifdef NATIVE_PORT\n'
    '#include "mdkr_trace.h"'),
   # queda:
   ('#ifdef NATIVE_PORT\n'
    '#include "enh_speedometer.h"   /* mdkr_enh_fps_draw */\n'
    '#endif\n'
    '#ifdef NATIVE_PORT\n'
    '#include "mdkr_trace.h"')),
  # --- game/src/menu.c (hunk 2) ---
  ('game/src/menu.c',
   # busca:
   ('    }\n'
    '    *currDisplayList = sMenuCurrDisplayList;'),
   # queda:
   ('    }\n'
    '#ifdef NATIVE_PORT\n'
    '    /* Contador de FPS con R3: el otro punto por cuadro. Va al final, ya dibujado el menu,\n'
    '     * para que el contador quede por encima y no lo tape nada. */\n'
    '    mdkr_enh_fps_draw(&sMenuCurrDisplayList);\n'
    '#endif\n'
    '    *currDisplayList = sMenuCurrDisplayList;')),
  # --- platform/platform_sdl_min.c (hunk 2) ---
  ('platform/platform_sdl_min.c',
   # busca:
   ('\n'
    '/* Translate one maintained SDL controller source into an N64 pad sample. */'),
   # queda:
   ('\n'
    '/* Contador de FPS con R3: la bandera la define platform/enh_speedometer.c. */\n'
    'extern int g_mdkr_mostrar_fps;\n'
    '\n'
    '/* Translate one maintained SDL controller source into an N64 pad sample. */')),
  # --- platform/platform_sdl_min.c (hunk 3) ---
  ('platform/platform_sdl_min.c',
   # busca:
   ('\n'
    '    /* Left stick -> analog (N64 range ±80; SDL axis is ±32767, +Y is down). */'),
   # queda:
   ('\n'
    '    /* Contador de FPS con R3. Se MIRA el boton, no se consume: `normalized` y\n'
    '     * `p->buttons` quedan como estaban, asi que si el jugador tiene R3 asignado a una accion del\n'
    '     * juego la sigue haciendo. */\n'
    '    {\n'
    '        static int r3_pulsado = 0;\n'
    '        const int r3 = source->buttons[SDL_CONTROLLER_BUTTON_RIGHTSTICK] != 0;\n'
    '\n'
    '        if (r3 && !r3_pulsado) {\n'
    '            g_mdkr_mostrar_fps = !g_mdkr_mostrar_fps;\n'
    '        }\n'
    '        r3_pulsado = r3;\n'
    '    }\n'
    '\n'
    '    /* Left stick -> analog (N64 range ±80; SDL axis is ±32767, +Y is down). */')),
]


def main():
    parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                     hecho='el contador de FPS y su conmutador R3, en los cinco archivos que lo sostienen')


if __name__ == '__main__':
    main()
