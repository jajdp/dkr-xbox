/* strings.h minimo para el port UWP de Diddy Kong Racing.
 *
 * Otra cabecera POSIX que MinGW aporta y el CRT de MSVC no. De ella el juego usa strcasecmp (42
 * veces) y ffs (3). Se mapean a los equivalentes de MSVC en vez de reimplementarlos.
 */
#ifndef MDKR_UWP_STRINGS_H
#define MDKR_UWP_STRINGS_H

#include <string.h>

#define strcasecmp  _stricmp
#define strncasecmp _strnicmp

/* ffs: indice (base 1) del bit menos significativo puesto; 0 si no hay ninguno.
 *
 * La version obvia seria _BitScanForward de <intrin.h>, y asi estuvo escrita, pero incluir
 * <intrin.h> aqui es una trampa: en esta compilacion las cabeceras propias de clang van DELANTE
 * de las de Visual Studio (hace falta, o el emmintrin.h de MSVC tapa las intrinsecas SSE2 y el
 * enlace se cae), asi que el <intrin.h> que entra es el de clang, que arrastra mmintrin.h y
 * define __m64 como vector -- justo despues de que windows.h ya lo haya definido como union.
 * El choque rompe la unidad entera.
 *
 * __builtin_ctz hace exactamente lo mismo sin cabecera ninguna: cuenta los ceros por abajo. */
static inline int ffs(int valor) {
    if (valor == 0) return 0;
    return __builtin_ctz((unsigned int) valor) + 1;
}

#endif /* MDKR_UWP_STRINGS_H */
