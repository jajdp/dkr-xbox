# -*- coding: utf-8 -*-
"""WebGPU sobre la CoreWindow de la consola, y la tercera rama de la costura de dialecto.

--- 1. La superficie ------------------------------------------------------------------------

En la consola la ventana no es un HWND: el sistema crea una CoreWindow y SDL2 la entrega como
IInspectable* en info.info.winrt.window. Hacen falta tres piezas, una por capa:

  platform_os.h       un valor mas en el enum de sistemas de ventanas (MDKR_WGPU_WINDOW_WINRT),
                      en vez de colgar un #ifdef del despachador: asi la eleccion sigue siendo
                      una sola
  platform_sdl_min.c  el caso SDL_SYSWM_WINRT, que devuelve ese puntero y nada mas (no hay
                      hinstance ni id numerico que rellenar)
  gfx_webgpu.c        la rama que construye el encadenado que Dawn espera

⚠ Dawn SI acepta una CoreWindow, pero con el nombre ANTIGUO del encadenado:
WGPUSurfaceDescriptorFromWindowsCoreWindow, no la nomenclatura WGPUSurfaceSource* del resto de ese
bloque. Buscar solo la nueva lleva a concluir, en falso, que Dawn no soporta UWP.

--- 2. La costura de dialecto ---------------------------------------------------------------

El port habla con WebGPU a traves de gfx_webgpu_compat.h, que tenia dos ramas: el navegador
(emdawnwebgpu) y wgpu-native. La consola no es ninguna de las dos:

  - la FORMA de la API es la de Dawn, como en la rama del navegador, porque emdawnwebgpu ES Dawn
    compilado a wasm;
  - el COMPORTAMIENTO es nativo, como en la rama de wgpu-native: hay presentacion explicita y no
    hay bucle de eventos de JS al que ceder.

Por que existe esta tercera rama y no se reutiliza wgpu-native: wgpu-native solo publica binarios
GNU/MinGW para Windows y su target de Rust para UWP es tier 3. Dawn si esta disponible para UWP,
ya compilado, en SternXD/uwp-dep (docs/DEPENDENCIES.md).

Todo lo de la rama esta verificado contra el webgpu.h de ESE Dawn, no supuesto.

--- 3. El unico ajuste que se pierde --------------------------------------------------------

El bloque de desiredMaximumFrameLatency usa WGPUSurfaceConfigurationExtras, que es extension
exclusiva de wgpu-native, e iba guardado con un #ifndef __EMSCRIPTEN__ dentro de gfx_webgpu.c --
una fuga de dialecto que la cabecera de la costura prohibe explicitamente. La decision pasa a la
costura, que es donde ese mismo archivo dice que debe vivir, con un flag que declaran las TRES
ramas. Solo afecta a cuantos cuadros van en vuelo, no a lo que se dibuja.

Idempotente y todo o nada; escritura atomica. Lo aplica tools/apply_uwp.py, que es el
punto de entrada: este script se puede correr solo, pero el orden y los requisitos los
comprueba aquel.

Uso: patch_webgpu.py <raiz del arbol de Golden Balloon>
"""
import parchear

TEMA = 'dkr-xbox: WebGPU on CoreWindow'

# Cada trío: archivo relativo a la raíz del árbol, texto que se busca, texto que queda.
CAMBIOS = [
  # --- platform/platform_os.h (hunk 1) ---
  ('platform/platform_os.h',
   # busca:
   ('    MDKR_WGPU_WINDOW_WAYLAND,\n'
    '};'),
   # queda:
   ('    MDKR_WGPU_WINDOW_WAYLAND,\n'
    '    /* UWP / Xbox Series X: la ventana no es un HWND sino una CoreWindow, que\n'
    '     * SDL2 entrega como IInspectable* en info.info.winrt.window y Dawn acepta\n'
    '     * tal cual. Se anade al enum en vez de colgar un #ifdef del despachador,\n'
    '     * para que la eleccion siga siendo una sola. */\n'
    '    MDKR_WGPU_WINDOW_WINRT,\n'
    '};')),
  # --- platform/platform_sdl_min.c (hunk 1) ---
  ('platform/platform_sdl_min.c',
   # busca:
   ('#endif\n'
    '#if defined(SDL_VIDEO_DRIVER_X11)'),
   # queda:
   ('#endif\n'
    '#if defined(SDL_VIDEO_DRIVER_WINRT)\n'
    '        /* UWP / Xbox: SDL2 devuelve la CoreWindow como IInspectable*. No hay\n'
    '         * hinstance ni id numerico que rellenar; Dawn solo quiere ese puntero. */\n'
    '        case SDL_SYSWM_WINRT:\n'
    '            if (out_window != NULL) {\n'
    '                *out_window = (void *)info.info.winrt.window;\n'
    '            }\n'
    '            return MDKR_WGPU_WINDOW_WINRT;\n'
    '#endif\n'
    '#if defined(SDL_VIDEO_DRIVER_X11)')),
  # --- platform/fast3d/gfx_webgpu.c (hunk 1) ---
  ('platform/fast3d/gfx_webgpu.c',
   # busca:
   ('            BRINGUP_SURFACE, wgpuInstanceCreateSurface(instance, &sd));\n'
    '    } else if (sys == MDKR_WGPU_WINDOW_X11) {'),
   # queda:
   ('            BRINGUP_SURFACE, wgpuInstanceCreateSurface(instance, &sd));\n'
    '#ifdef MDKR_DAWN_NATIVE\n'
    '    } else if (sys == MDKR_WGPU_WINDOW_WINRT) {\n'
    '        /* UWP / Xbox Series X. Dawn SI acepta una CoreWindow, pero con el\n'
    '         * nombre antiguo del encadenado: WGPUSurfaceDescriptorFromWindowsCoreWindow,\n'
    '         * no la nomenclatura WGPUSurfaceSource* del resto de este bloque. Buscar\n'
    '         * solo la nueva lleva a concluir, en falso, que Dawn no soporta UWP.\n'
    '         * Verificado contra el webgpu.h de uwp-dep, que es el Dawn con el que se\n'
    '         * enlaza, y contra otro port UWP que ya usa ese mismo Dawn. */\n'
    '        WGPUSurfaceDescriptorFromWindowsCoreWindow cw = {0};\n'
    '        cw.chain.sType = WGPUSType_SurfaceDescriptorFromWindowsCoreWindow;\n'
    '        cw.coreWindow = window_handle;\n'
    '        sd.nextInChain = (WGPUChainedStruct *)&cw;\n'
    '        return WGPU_FAULT_CREATE(\n'
    '            BRINGUP_SURFACE, wgpuInstanceCreateSurface(instance, &sd));\n'
    '#endif  /* MDKR_DAWN_NATIVE: el encadenado de CoreWindow no existe en wgpu-native */\n'
    '    } else if (sys == MDKR_WGPU_WINDOW_X11) {')),
  # --- platform/fast3d/gfx_webgpu.c (hunk 2) ---
  ('platform/fast3d/gfx_webgpu.c',
   # busca:
   ('    cfg.presentMode = wgpu_choose_present_mode();   /* PERF-051: FIFO default (vsync), GE007_WEBGPU_PRESENT opt-in */\n'
    '#ifndef __EMSCRIPTEN__\n'
    '    /* Pin the swap chain to one frame in flight (see'),
   # queda:
   ('    cfg.presentMode = wgpu_choose_present_mode();   /* PERF-051: FIFO default (vsync), GE007_WEBGPU_PRESENT opt-in */\n'
    '#if WGPU_COMPAT_HAS_FRAME_LATENCY_EXTRAS\n'
    '    /* Pin the swap chain to one frame in flight (see')),
  # --- platform/fast3d/gfx_webgpu_compat.h (hunk 1) ---
  ('platform/fast3d/gfx_webgpu_compat.h',
   # busca:
   ('  /* Web WebGPU exposes pass-boundary timestamps in nanoseconds but not\n'
    '   * wgpu-native\'s optional in-pass extension. */\n'
    '  #define WGPU_COMPAT_TIMESTAMP_PERIOD(queue) ((void)(queue), 1.0f)\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_SUPPORTED(adapter) \\\n'
    '      ((void)(adapter), false)\n'
    '  #define WGPU_COMPAT_DEVICE_TIMESTAMP_INSIDE_PASS_SUPPORTED(device) \\\n'
    '      ((void)(device), false)\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_FEATURE \\\n'
    '      ((WGPUFeatureName)0)\n'
    '  #define WGPU_COMPAT_WRITE_PASS_TIMESTAMP(pass, query_set, index) \\\n'
    '      do { (void)(pass); (void)(query_set); (void)(index); } while (0)'),
   # queda:
   ('  /* El bloque de desiredMaximumFrameLatency usa una extension de wgpu-native;\n'
    '   * el navegador nunca lo compilo. Ahora lo decide la costura. */\n'
    '  #define WGPU_COMPAT_HAS_FRAME_LATENCY_EXTRAS 0\n'
    '  /* Web WebGPU exposes pass-boundary timestamps in nanoseconds but not\n'
    '   * wgpu-native\'s optional in-pass extension. */\n'
    '  #define WGPU_COMPAT_TIMESTAMP_PERIOD(queue) ((void)(queue), 1.0f)\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_SUPPORTED(adapter) \\\n'
    '      ((void)(adapter), false)\n'
    '  #define WGPU_COMPAT_DEVICE_TIMESTAMP_INSIDE_PASS_SUPPORTED(device) \\\n'
    '      ((void)(device), false)\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_FEATURE \\\n'
    '      ((WGPUFeatureName)0)\n'
    '  #define WGPU_COMPAT_WRITE_PASS_TIMESTAMP(pass, query_set, index) \\\n'
    '      do { (void)(pass); (void)(query_set); (void)(index); } while (0)\n'
    '#elif defined(MDKR_DAWN_NATIVE)\n'
    '  /* ---------------------------------------------------------------------\n'
    '   * Dawn NATIVO (port UWP / Xbox Series X, 2026-09-14).\n'
    '   *\n'
    '   * Tercera rama de la costura. No es ninguna de las dos anteriores:\n'
    '   *   - la FORMA de la API es la de Dawn, como en la rama del navegador,\n'
    '   *     porque emdawnwebgpu ES Dawn compilado a wasm;\n'
    '   *   - el COMPORTAMIENTO es nativo, como en la rama de wgpu-native: aqui hay\n'
    '   *     presentacion explicita y no hay bucle de eventos de JS al que ceder.\n'
    '   *\n'
    '   * Por que existe: wgpu-native solo publica prebuilt GNU/MinGW para Windows\n'
    '   * y no hay forma de llevarlo a UWP (su target de Rust es tier 3). Dawn si\n'
    '   * esta disponible para UWP, ya compilado, en SternXD/uwp-dep, que es de\n'
    '   * donde lo toma este port (docs/DEPENDENCIES.md).\n'
    '   *\n'
    '   * Todo lo de aqui esta verificado contra el webgpu.h de ESE Dawn, no\n'
    '   * supuesto. Dos diferencias con la rama del navegador que conviene saber:\n'
    '   * este Dawn es mas nuevo, asi que SI define WGPU_TRUE/WGPU_FALSE y SI lleva\n'
    '   * el parametro `message` en los callbacks.\n'
    '   * ------------------------------------------------------------------- */\n'
    '  #include <webgpu/webgpu.h>          /* puente a dawn/webgpu.h             */\n'
    '\n'
    '  /* Dawn no tiene wgpuDevicePoll (es extension de wgpu-native): su bombeo es\n'
    '   * por instancia. No se cede a ningun bucle externo — los call-sites ya\n'
    '   * iteran hasta que la condicion se cumple. */\n'
    '  #define WGPU_COMPAT_PUMP(instance, device)                            \\\n'
    '      do {                                                              \\\n'
    '          (void)(device);                                               \\\n'
    '          if (instance) wgpuInstanceProcessEvents((instance));          \\\n'
    '      } while (0)\n'
    '  /* A diferencia de wgpu-native, en Dawn TODO callback es un future que solo\n'
    '   * se despacha dentro de ProcessEvents. Aunque las pipelines se creen por la\n'
    '   * via sincrona, drenar aqui cuesta nada y evita dejar futures colgados. */\n'
    '  #define WGPU_COMPAT_DRAIN(instance)                                   \\\n'
    '      do { if (instance) wgpuInstanceProcessEvents((instance)); } while (0)\n'
    '  /* Verificado en dawn/webgpu.h: el callback SI lleva `message`, igual que\n'
    '   * wgpu-native y al contrario que el emdawnwebgpu de la rama de arriba. */\n'
    '  #define WGPU_COMPAT_QUEUE_DONE_CALLBACK(name)                         \\\n'
    '      static void name(WGPUQueueWorkDoneStatus status,                  \\\n'
    '                       WGPUStringView message, void *userdata,          \\\n'
    '                       void *userdata2)\n'
    '  #define WGPU_COMPAT_QUEUE_DONE_UNUSED()                               \\\n'
    '      do { (void)message; (void)userdata2; } while (0)\n'
    '  #define WGPU_COMPAT_QUEUE_ON_DONE(queue, cb, userdata_value)          \\\n'
    '      do {                                                              \\\n'
    '          WGPUQueueWorkDoneCallbackInfo _wc_info =                      \\\n'
    '              WGPU_QUEUE_WORK_DONE_CALLBACK_INFO_INIT;                  \\\n'
    '          _wc_info.mode = WGPUCallbackMode_AllowProcessEvents;          \\\n'
    '          _wc_info.callback = (cb);                                     \\\n'
    '          _wc_info.userdata1 = (userdata_value);                        \\\n'
    '          (void)wgpuQueueOnSubmittedWorkDone((queue), _wc_info);        \\\n'
    '      } while (0)\n'
    '  #define WGPU_COMPAT_QUEUE_POLL(instance, device)                      \\\n'
    '      do {                                                              \\\n'
    '          (void)(device);                                               \\\n'
    '          if (instance) wgpuInstanceProcessEvents((instance));          \\\n'
    '      } while (0)\n'
    '  /* Dawn si sabe bloquear, con wgpuInstanceWaitAny, pero esa llamada necesita\n'
    '   * el WGPUFuture concreto y la costura no lo transporta: sus macros solo\n'
    '   * reciben (instance, device). Antes que inventar un canal para el future se\n'
    '   * declara que aqui no se bloquea, que es lo que ya hace la rama del\n'
    '   * navegador: el call-site salta el intento de dibujado cuando la cola esta\n'
    '   * saturada. Si algun dia hace falta bloquear de verdad, el cambio es\n'
    '   * ampliar la costura, no parchear este macro. */\n'
    '  #define WGPU_COMPAT_QUEUE_CAN_BLOCK 0\n'
    '  #define WGPU_COMPAT_QUEUE_BLOCK(instance, device)                     \\\n'
    '      WGPU_COMPAT_QUEUE_POLL((instance), (device))\n'
    '  /* Nativo: la presentacion es explicita, como en wgpu-native. */\n'
    '  #define WGPU_COMPAT_PRESENT(surface) wgpuSurfacePresent((surface))\n'
    '  /* Nativo: el bombeo es sincrono, sin el clamp de setTimeout del navegador. */\n'
    '  #define WGPU_COMPAT_BRINGUP_WAIT_ITERS 1000\n'
    '  /* Nativo: se conserva el barrido que prefiere BGRA8, para no mover el\n'
    '   * formato del objetivo de escena ni el swizzle de lectura. */\n'
    '  #define WGPU_COMPAT_PREFER_FIRST_SURFACE_FORMAT 0\n'
    '  /* Dawn no define el estado _Occluded (verificado: sus estados son\n'
    '   * SuccessOptimal, SuccessSuboptimal, Timeout, Outdated, Lost, Error). */\n'
    '  #define WGPU_COMPAT_SURFACE_OCCLUDED(status) ((void)(status), false)\n'
    '  #define WGPU_COMPAT_SURFACE_USAGES_REPORTED 1\n'
    '  /* WGPUSurfaceConfigurationExtras es extension de wgpu-native y Dawn no la\n'
    '   * tiene, asi que no se puede fijar desiredMaximumFrameLatency: la cadena de\n'
    '   * intercambio se queda con la profundidad por omision del backend. Es el\n'
    '   * unico ajuste que se pierde al cambiar de dialecto, y solo afecta a cuantos\n'
    '   * cuadros van en vuelo, no a lo que se dibuja. */\n'
    '  #define WGPU_COMPAT_HAS_FRAME_LATENCY_EXTRAS 0\n'
    '  /* Dawn entrega las marcas de tiempo ya en nanosegundos y no expone el\n'
    '   * wgpuQueueGetTimestampPeriod de wgpu-native. */\n'
    '  #define WGPU_COMPAT_TIMESTAMP_PERIOD(queue) ((void)(queue), 1.0f)\n'
    '  /* Dawn SI tiene marcas dentro del paso, con otro nombre:\n'
    '   * ChromiumExperimentalTimestampQueryInsidePasses. Se aprovecha en vez de\n'
    '   * renunciar a ellas como hace la rama del navegador. */\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_SUPPORTED(adapter)          \\\n'
    '      (wgpuAdapterHasFeature(                                           \\\n'
    '           (adapter),                                                   \\\n'
    '           WGPUFeatureName_ChromiumExperimentalTimestampQueryInsidePasses) != 0)\n'
    '  #define WGPU_COMPAT_DEVICE_TIMESTAMP_INSIDE_PASS_SUPPORTED(device)    \\\n'
    '      (wgpuDeviceHasFeature(                                            \\\n'
    '           (device),                                                    \\\n'
    '           WGPUFeatureName_ChromiumExperimentalTimestampQueryInsidePasses) != 0)\n'
    '  #define WGPU_COMPAT_TIMESTAMP_INSIDE_PASS_FEATURE                     \\\n'
    '      (WGPUFeatureName_ChromiumExperimentalTimestampQueryInsidePasses)\n'
    '  #define WGPU_COMPAT_WRITE_PASS_TIMESTAMP(pass, query_set, index)      \\\n'
    '      wgpuRenderPassEncoderWriteTimestamp((pass), (query_set), (index))')),
  # --- platform/fast3d/gfx_webgpu_compat.h (hunk 2) ---
  ('platform/fast3d/gfx_webgpu_compat.h',
   # busca:
   ('  #define WGPU_COMPAT_SURFACE_USAGES_REPORTED 1\n'
    '  /* wgpu-native returns raw timestamp ticks and publishes their nanosecond'),
   # queda:
   ('  #define WGPU_COMPAT_SURFACE_USAGES_REPORTED 1\n'
    '  /* wgpu-native SI trae WGPUSurfaceConfigurationExtras, con la que se fija\n'
    '   * desiredMaximumFrameLatency en cada re-configuracion de la superficie. */\n'
    '  #define WGPU_COMPAT_HAS_FRAME_LATENCY_EXTRAS 1\n'
    '  /* wgpu-native returns raw timestamp ticks and publishes their nanosecond')),
]


def main():
    parchear.informe(*parchear.aplicar_varios(parchear.raiz(), CAMBIOS, TEMA),
                     hecho='platform_os.h, platform_sdl_min.c, gfx_webgpu.c y la costura: superficie CoreWindow y rama Dawn nativo')


if __name__ == '__main__':
    main()
