/* uwp_compat.h — capa de compatibilidad del port UWP de Diddy Kong Racing.
 *
 * Se mete en la compilacion con -include, no con #include: asi el codigo del juego no se toca y
 * la capa entera vive en un archivo, que es lo que se quiere cuando el upstream sigue vivo y
 * habra que rebasar sus cambios.
 *
 * Cubre lo que el sondeo del 2026-09-14 encontro al compilar platform/ con las cabeceras REALES
 * de UWP (--target=x86_64-pc-windows-msvc -DWINAPI_FAMILY=WINAPI_FAMILY_APP). Seis simbolos en
 * seis archivos; nada mas. Las cabeceras POSIX que faltan (dirent.h, strings.h) van aparte, en
 * esta misma carpeta, porque un -include no puede satisfacer un #include.
 */
#ifndef MDKR_UWP_COMPAT_H
#define MDKR_UWP_COMPAT_H

/* Esta cabecera se fuerza en TODAS las unidades, asi que windows.h entra en archivos que nunca
 * lo incluyeron. Eso arrastra macros heredadas que pisan identificadores legitimos del juego:
 *   - windef.h define `near` y `far` (herencia de los 16 bits) -> rompe gu_port.c, que los usa
 *     como nombres de variable en las matrices de proyeccion
 *   - wingdi.h define `TRANSPARENT` y `OPAQUE` -> rompen el enum TextureRenderModes
 * Se recortan las partes que no hacen falta y se deshacen esas cuatro macros. Deshacerlas es mas
 * quirurgico que NOGDI, que se llevaria por delante cosas que si se usan. */
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#undef near
#undef far
#undef TRANSPARENT
#undef OPAQUE
/* Ojo con el efecto colateral: windef.h define `FAR` como `far` y `NEAR` como `near`, asi que
 * deshacer las minusculas deja a las mayusculas expandiendose a un identificador inexistente.
 * combaseapi.h las usa en sus declaraciones (`LPSTREAM FAR * ppstm`) y el SDK deja de compilar.
 * Se redefinen vacias, que es lo que valen hoy: son herencia de los punteros de 16 bits. */
#undef FAR
#undef NEAR
#define FAR
#define NEAR

/* SDL_endian.h de SDL2 define _m_prefetch a mano «hasta que arreglen el problema de Clang 11»,
 * y en clang 22 eso ya es un builtin: redefinirlo es error. No es fallo del juego, es un apano
 * de SDL2 que envejecio.
 *
 * SDL protege su parche con #ifndef __PRFCHWINTRIN_H, que es el include-guard de la cabecera de
 * clang, asi que basta con declarar esa guarda para que se lo salte. Se probo antes incluir
 * <intrin.h> entero para lograr lo mismo y fue PEOR: metido tan temprano en todas las unidades
 * provoca choques de builtins en seis archivos mas. Definir la guarda es la version quirurgica. */
#ifndef __PRFCHWINTRIN_H
#define __PRFCHWINTRIN_H
#endif

#include <errno.h>
#include <time.h>
#include <string.h>

/* --------------------------------------------------------------------------
 * _getpid  (text_state_file.c, user_paths.c, video_config_runtime.c)
 * El CRT de UWP no lo expone. GetCurrentProcessId da lo mismo y si esta
 * permitida dentro de un AppContainer.
 * ----------------------------------------------------------------------- */
static inline int mdkr_uwp_getpid(void) { return (int)GetCurrentProcessId(); }
#define _getpid() mdkr_uwp_getpid()

/* --------------------------------------------------------------------------
 * clock_gettime / nanosleep  (gfx_webgpu.c, present_sched.c)
 * POSIX puro: no existen en el CRT de MSVC en ninguna familia. Se reimplementan
 * sobre el contador de alta resolucion, que es lo que usaria uno a mano.
 * ----------------------------------------------------------------------- */
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
#endif
#ifndef CLOCK_REALTIME
#define CLOCK_REALTIME 0
#endif

static inline int mdkr_uwp_clock_gettime(int reloj, struct timespec *ts) {
    LARGE_INTEGER frecuencia, cuenta;
    (void)reloj;                      /* aqui los dos relojes salen del mismo contador */
    if (ts == NULL) { errno = EFAULT; return -1; }
    if (!QueryPerformanceFrequency(&frecuencia) || frecuencia.QuadPart == 0) {
        errno = EINVAL;
        return -1;
    }
    QueryPerformanceCounter(&cuenta);
    ts->tv_sec  = (time_t)(cuenta.QuadPart / frecuencia.QuadPart);
    /* El resto se pasa a nanosegundos ANTES de dividir, para no perder precision. */
    ts->tv_nsec = (long)(((cuenta.QuadPart % frecuencia.QuadPart) * 1000000000LL)
                         / frecuencia.QuadPart);
    return 0;
}
#define clock_gettime(reloj, ts) mdkr_uwp_clock_gettime((reloj), (ts))

static inline int mdkr_uwp_nanosleep(const struct timespec *pedido,
                                     struct timespec *restante) {
    DWORD ms;
    if (pedido == NULL) { errno = EFAULT; return -1; }
    if (restante != NULL) { restante->tv_sec = 0; restante->tv_nsec = 0; }
    /* Sleep solo tiene resolucion de milisegundo. Se redondea HACIA ARRIBA: dormir
     * de menos en un planificador de cuadros haria girar el bucle en vacio. */
    ms = (DWORD)(pedido->tv_sec * 1000LL + (pedido->tv_nsec + 999999LL) / 1000000LL);
    Sleep(ms);
    return 0;
}
#define nanosleep(pedido, restante) mdkr_uwp_nanosleep((pedido), (restante))

/* --------------------------------------------------------------------------
 * strtok_r  (platform_sdl_min.c)
 * Reentrante de POSIX. MSVC trae la misma idea con otro nombre y el mismo
 * contrato: strtok_s con tres argumentos.
 * ----------------------------------------------------------------------- */
#define strtok_r(cadena, separadores, contexto) \
    strtok_s((cadena), (separadores), (contexto))

/* --------------------------------------------------------------------------
 * CreateFileW  (fs_utf8.c)
 * WINAPI_FAMILY_APP la esconde; su sustituta en UWP es CreateFile2, que recibe
 * los atributos en una estructura aparte en vez de como parametros sueltos.
 * ----------------------------------------------------------------------- */
static inline HANDLE mdkr_uwp_CreateFileW(LPCWSTR nombre, DWORD acceso, DWORD comparticion,
                                          LPSECURITY_ATTRIBUTES seguridad, DWORD disposicion,
                                          DWORD atributos, HANDLE plantilla) {
    CREATEFILE2_EXTENDED_PARAMETERS ext;
    (void)plantilla;                  /* CreateFile2 no admite fichero plantilla */
    ZeroMemory(&ext, sizeof(ext));
    ext.dwSize               = sizeof(ext);
    ext.dwFileAttributes     = atributos & 0x0000FFFFu;   /* atributos, sin las banderas */
    ext.dwFileFlags          = atributos & 0xFFF00000u;   /* FILE_FLAG_*                */
    ext.dwSecurityQosFlags   = atributos & 0x000F0000u;   /* SECURITY_*                 */
    ext.lpSecurityAttributes = seguridad;
    return CreateFile2(nombre, acceso, comparticion, disposicion, &ext);
}
#define CreateFileW(n, a, c, s, d, at, p) mdkr_uwp_CreateFileW((n), (a), (c), (s), (d), (at), (p))

/* --------------------------------------------------------------------------
 * _wexecv / _wspawnvp  (fs_utf8.c)
 * UWP PROHIBE lanzar procesos, no es que falte la funcion: una app en
 * AppContainer no puede crear otro proceso ni reemplazarse a si misma. No hay
 * equivalente que poner, asi que se declaran fallando con ENOSYS y quien llama
 * ya trata el error (devuelven errno, que es lo que fs_utf8.c propaga).
 *
 * A quien afecta, comprobado:
 *   - app/app_relaunch.cpp  -> relanzar el juego tras un cambio de ajustes
 *   - app/ui_settings.cpp   -> lanzar un programa externo desde los ajustes
 * Las dos son funciones del lanzador de escritorio, no del juego. En la consola
 * quedaran inertes y devolviendo error, que es el comportamiento honesto.
 * ----------------------------------------------------------------------- */
static inline intptr_t mdkr_uwp_sin_procesos(void) { errno = ENOSYS; return -1; }
#define _wexecv(imagen, argv)          ((intptr_t)mdkr_uwp_sin_procesos())
#define _wspawnvp(modo, imagen, argv)  ((intptr_t)mdkr_uwp_sin_procesos())
#ifndef _P_WAIT
#define _P_WAIT 0
#endif

#endif /* MDKR_UWP_COMPAT_H */
