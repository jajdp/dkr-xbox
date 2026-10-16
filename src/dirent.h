/* dirent.h minimo para el port UWP de Diddy Kong Racing.
 *
 * El CRT de MSVC no trae dirent.h -- es POSIX, y MinGW lo aporta por su cuenta. Siete archivos
 * de platform/ lo incluyen y usan solo opendir/readdir/closedir, struct dirent, d_name y d_type.
 * Esto lo implementa sobre FindFirstFileExW/FindNextFileW, que SI estan permitidas dentro de un
 * AppContainer (a diferencia de FindFirstFileA, que la familia WINAPI_FAMILY_APP esconde).
 *
 * Todo es `static inline`: cada unidad de compilacion se lleva su copia, que en C no da
 * problemas de simbolo duplicado y evita tener que sumar un .c al build.
 *
 * Alcance deliberado: NO implementa seekdir/telldir/rewinddir/scandir porque este juego no los
 * usa. Si algun dia hicieran falta, se anaden aqui; dejar la cabecera incompleta a proposito es
 * mejor que fingir una implementacion POSIX completa que nadie ha probado.
 */
#ifndef MDKR_UWP_DIRENT_H
#define MDKR_UWP_DIRENT_H

#include <windows.h>
#include <stdlib.h>
#include <string.h>

#define DT_UNKNOWN 0
#define DT_REG     8
#define DT_DIR     4

struct dirent {
    unsigned char d_type;
    char          d_name[MAX_PATH * 4];   /* MAX_PATH en UTF-8, con holgura */
};

typedef struct {
    HANDLE           handle;
    WIN32_FIND_DATAW data;
    int              primera;     /* la primera entrada ya viene en el FindFirstFileEx */
    int              agotado;
    struct dirent    entrada;
} MDKR_DIR;

#define DIR MDKR_DIR

static inline void mdkr_uwp_dirent_rellena(MDKR_DIR *d) {
    d->entrada.d_type =
        (d->data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ? DT_DIR : DT_REG;
    d->entrada.d_name[0] = '\0';
    WideCharToMultiByte(CP_UTF8, 0, d->data.cFileName, -1,
                        d->entrada.d_name, (int)sizeof(d->entrada.d_name),
                        NULL, NULL);
}

static inline MDKR_DIR *opendir(const char *ruta) {
    MDKR_DIR *d;
    wchar_t  *patron;
    int       n;
    size_t    largo;

    if (ruta == NULL) return NULL;

    /* Se le pega "\*" a la ruta para que FindFirstFileEx enumere su contenido. */
    n = MultiByteToWideChar(CP_UTF8, 0, ruta, -1, NULL, 0);
    if (n <= 0) return NULL;
    largo = (size_t)n + 3u;
    patron = (wchar_t *)calloc(largo, sizeof(wchar_t));
    if (patron == NULL) return NULL;
    MultiByteToWideChar(CP_UTF8, 0, ruta, -1, patron, n);
    largo = wcslen(patron);
    if (largo > 0 && patron[largo - 1] != L'\\' && patron[largo - 1] != L'/') {
        patron[largo++] = L'\\';
    }
    patron[largo++] = L'*';
    patron[largo] = L'\0';

    d = (MDKR_DIR *)calloc(1, sizeof(MDKR_DIR));
    if (d == NULL) { free(patron); return NULL; }

    d->handle = FindFirstFileExW(patron, FindExInfoBasic, &d->data,
                                 FindExSearchNameMatch, NULL, 0);
    free(patron);
    if (d->handle == INVALID_HANDLE_VALUE) { free(d); return NULL; }
    d->primera = 1;
    return d;
}

static inline struct dirent *readdir(MDKR_DIR *d) {
    if (d == NULL || d->agotado) return NULL;
    if (d->primera) {
        d->primera = 0;
    } else if (!FindNextFileW(d->handle, &d->data)) {
        d->agotado = 1;
        return NULL;
    }
    mdkr_uwp_dirent_rellena(d);
    return &d->entrada;
}

static inline int closedir(MDKR_DIR *d) {
    if (d == NULL) return -1;
    if (d->handle != INVALID_HANDLE_VALUE) FindClose(d->handle);
    free(d);
    return 0;
}

#endif /* MDKR_UWP_DIRENT_H */
