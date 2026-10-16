/* Punto de entrada del port UWP de Diddy Kong Racing.
 *
 * En escritorio el juego arranca por main() (platform/main_pc.c) y SDL abre una ventana Win32.
 * En la consola no hay ventana que abrir: el sistema crea un CoreWindow y se lo entrega a la
 * aplicacion, que debe presentarse como un IFrameworkView y cederle el hilo. Ese baile lo hace
 * SDL por dentro -- SDL_WinRTRunApp registra su propia vista, llama a CoreApplication::Run y,
 * cuando el CoreWindow ya existe, invoca la funcion que se le pase como si fuera main().
 *
 * Por que no se usa la plantilla de SDL: la suya es C++/CX ([Platform::MTAThread], ^, ref new),
 * que solo compila con cl.exe /ZW. Todo este port va con clang, que no habla C++/CX. Lo que hace
 * la plantilla son dos cosas, y las dos se pueden escribir en C++ normal:
 *
 *   1. [Platform::MTAThread]  -> inicializar el apartamento como multihilo. CoreApplication::Run
 *      lo exige, y aqui se hace a mano con RoInitialize(RO_INIT_MULTITHREADED).
 *   2. llamar a SDL_WinRTRunApp, que es C y ya viene compilado dentro de SDL2.lib.
 *
 * Asi que no hace falta cl.exe ni una segunda cadena de herramientas: el ejecutable entero sale
 * de clang + ld.lld.
 */
#include <windows.h>
#include <roapi.h>
#include <stdio.h>
#include <io.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifndef SDL_MAIN_HANDLED
#define SDL_MAIN_HANDLED
#endif
#include <SDL.h>
#include <SDL_main.h>

/* El motor. Con -DMDKR_APP=OFF (la configuracion del port de consola) main() vuelve a
 * platform/main_pc.c, que es exactamente el arranque que queremos envolver. */
extern "C" int main(int argc, char **argv);

/* main_pc.c resuelve la ROM por defecto como ruta RELATIVA ("baserom.us.v80.z64"), contra el
 * directorio actual. En escritorio eso es la carpeta desde la que se lanza el juego; dentro de
 * un AppContainer el directorio actual no es algo con lo que convenga contar. La ROM viaja en el
 * paquete, junto al ejecutable, asi que se calcula esa ruta y se le pasa explicita.
 *
 * GetModuleFileNameW SI esta permitida en la familia WINAPI_FAMILY_APP, a diferencia de casi
 * todo lo demas que sirve para averiguar donde estas. */
static char *mdkr_uwp_ruta_rom(void) {
    static const wchar_t NOMBRE[] = L"baserom.us.v80.z64";
    wchar_t ancha[MAX_PATH * 2];
    DWORD n = GetModuleFileNameW(NULL, ancha, (DWORD) (sizeof(ancha) / sizeof(ancha[0])));
    if (n == 0 || n >= sizeof(ancha) / sizeof(ancha[0])) {
        return NULL;
    }
    /* se recorta el nombre del ejecutable y queda el directorio de instalacion */
    while (n > 0 && ancha[n - 1] != L'\\' && ancha[n - 1] != L'/') {
        n--;
    }
    ancha[n] = L'\0';
    if (wcslen(ancha) + wcslen(NOMBRE) + 1 >= sizeof(ancha) / sizeof(ancha[0])) {
        return NULL;
    }
    wcscat(ancha, NOMBRE);

    int bytes = WideCharToMultiByte(CP_UTF8, 0, ancha, -1, NULL, 0, NULL, NULL);
    if (bytes <= 0) {
        return NULL;
    }
    char *utf8 = (char *) malloc((size_t) bytes);
    if (utf8 == NULL) {
        return NULL;
    }
    WideCharToMultiByte(CP_UTF8, 0, ancha, -1, utf8, bytes, NULL, NULL);
    return utf8;
}

/* Manda stdout y stderr a un archivo dentro de LocalState.
 *
 * En la consola no hay terminal, asi que todo lo que el juego cuenta de si mismo se perdia: el
 * adaptador de WebGPU que eligio, la validacion de la ROM y, sobre todo, el callback
 * «[webgpu] device error», que es lo que Dawn dispara cuando rechaza una tuberia o un sombreador.
 * Sin eso, depurar un fallo de dibujado en una Xbox es adivinar.
 *
 * La carpeta se pide a SDL_GetPrefPath, que en el backend WinRT resuelve a LocalState y ya se sabe
 * que funciona aqui (es donde el juego guarda las partidas). Se llama desde dentro del arranque
 * que invoca SDL, no desde WinMain, porque para entonces el CoreWindow ya existe. */
static void mdkr_uwp_abrir_registro(void) {
    char *base = SDL_GetPrefPath("mdkr64", "mdkr64");
    if (base == NULL) {
        return;
    }
    size_t largo = strlen(base) + 32;
    char *ruta = (char *) malloc(largo);
    if (ruta != NULL) {
        snprintf(ruta, largo, "%sregistro.txt", base);
        /* Los DOS flujos se abren en modo «a». No es un detalle: con stdout en «w» y stderr en
         * «a» cada uno lleva su propia posicion sobre el mismo archivo y se pisan las escrituras
         * (en el primer registro salio un parentesis suelto en mitad de una linea). Y duplicar el
         * descriptor con _dup2 tampoco vale: arregla el descriptor pero deja el FILE* de stderr
         * con su bandera de error puesta, asi que enmudece del todo. En modo «a» cada escritura
         * salta al final por su cuenta y los dos conviven.
         *
         * El archivo se trunca aparte, para que cada arranque empiece limpio. */
        FILE *trunca = fopen(ruta, "w");
        if (trunca != NULL) {
            fclose(trunca);
        }
        if (freopen(ruta, "a", stdout) != NULL) {
            setvbuf(stdout, NULL, _IONBF, 0);
        }
        clearerr(stderr);
        if (freopen(ruta, "a", stderr) != NULL) {
            setvbuf(stderr, NULL, _IONBF, 0);
        }
        free(ruta);
    }
    SDL_free(base);
}

/* Argumentos extra de diagnostico, leidos de un archivo en LocalState.
 *
 * En la consola no hay linea de ordenes: la activacion no trae argumentos y no hay forma de
 * pedirle al juego una corrida controlada. Con esto, cada linea de
 * LocalState\mdkr64\mdkr64\diagnostico.txt se anade a argv.
 *
 * Lo que vuelve esto util de verdad es --headless-frames N: el juego corre un numero EXACTO de
 * cuadros, sale por su camino normal (imprimiendo [PTRREG], [TEXCACHE], [TEX] y los contadores de
 * GPU, que solo se escriben al apagarse) y la corrida es reproducible. La misma orden en el PC da
 * una referencia comparable cuadro a cuadro, en vez de «mas o menos por el mismo punto».
 *
 * Gobernado por un archivo y no por un #define a proposito: el binario que se diagnostica queda
 * EXACTAMENTE igual al que se juega. Sin el archivo, esto no existe.
 */
#define MDKR_UWP_MAX_ARGS 24

static int mdkr_uwp_args_extra(char **destino, int tope) {
    char *base = SDL_GetPrefPath("mdkr64", "mdkr64");
    if (base == NULL) {
        return 0;
    }
    int puestos = 0;
    size_t largo = strlen(base) + 32;
    char *ruta = (char *) malloc(largo);
    if (ruta != NULL) {
        snprintf(ruta, largo, "%sdiagnostico.txt", base);
        FILE *f = fopen(ruta, "r");
        if (f != NULL) {
            char linea[256];
            while (puestos < tope && fgets(linea, (int) sizeof(linea), f) != NULL) {
                size_t n = strlen(linea);
                while (n > 0 && (linea[n - 1] == '\n' || linea[n - 1] == '\r' ||
                                 linea[n - 1] == ' ' || linea[n - 1] == '\t')) {
                    linea[--n] = '\0';
                }
                if (n == 0) {
                    continue;
                }
                /* NOMBRE=VALOR va al entorno; lo demas, a argv.
                 *
                 * Casi toda la instrumentacion del juego se enciende por variables de entorno
                 * (MDKR_STATE_HASH, MDKR_TRACE...) y en UWP getenv() siempre devuelve NULL: el
                 * proceso arranca sin bloque de entorno. Pero el CRT guarda su propia copia
                 * dentro del proceso, asi que _putenv_s la escribe y getenv la lee. Es lo que
                 * pone esas herramientas al alcance en la consola. */
                char *igual = strchr(linea, '=');
                if (igual != NULL && linea[0] != '-') {
                    *igual = '\0';
                    _putenv_s(linea, igual + 1);
                    fprintf(stderr, "[uwp] entorno %s=%s\n", linea, igual + 1);
                    continue;
                }
                char *copia = (char *) malloc(n + 1);
                if (copia == NULL) {
                    break;
                }
                memcpy(copia, linea, n + 1);
                destino[puestos++] = copia;
            }
            fclose(f);
            if (puestos > 0) {
                fprintf(stderr, "[uwp] %d argumento(s) de diagnostico\n", puestos);
            }
        }
        free(ruta);
    }
    SDL_free(base);
    return puestos;
}

/* No se le pasa &main a SDL directamente: tomar la direccion de main no esta permitido en C++.
 * Este envoltorio cuesta nada, deja el codigo dentro de lo que el estandar admite y ademas es
 * donde se completa la linea de ordenes con la ruta de la ROM. */
static int SDLCALL mdkr_uwp_arranque(int argc, char **argv) {
    char *rom;
    char *propios[2 + MDKR_UWP_MAX_ARGS + 1];

    mdkr_uwp_abrir_registro();

    /* Si la activacion ya trajo un argumento que no es una opcion, manda ese: asi se puede
     * lanzar con otra ROM desde el Device Portal sin tocar el binario. */
    for (int i = 1; i < argc; i++) {
        if (argv[i] != NULL && argv[i][0] != '-') {
            return main(argc, argv);
        }
    }

    rom = mdkr_uwp_ruta_rom();
    if (rom == NULL) {
        return main(argc, argv);      /* que falle por la via normal, con su mensaje */
    }
    propios[0] = (argc > 0 && argv != NULL) ? argv[0] : (char *) "mdkr64";
    propios[1] = rom;
    int n = 2 + mdkr_uwp_args_extra(&propios[2], MDKR_UWP_MAX_ARGS);
    propios[n] = NULL;
    return main(n, propios);
}

int WINAPI WinMain(HINSTANCE instancia, HINSTANCE anterior, LPSTR linea, int mostrar) {
    (void) instancia;
    (void) anterior;
    (void) linea;
    (void) mostrar;

    /* Multihilo, no monohilo: CoreApplication::Run reclama un apartamento MTA. Si esto falla no
     * se sigue, porque lo siguiente seria un cuelgue sin explicacion en la consola. */
    HRESULT hr = RoInitialize(RO_INIT_MULTITHREADED);
    if (FAILED(hr) && hr != S_FALSE && hr != RPC_E_CHANGED_MODE) {
        return (int) hr;
    }

    /* El boton B del mando no cierra el juego.
     *
     * En la consola, B no es solo un boton: el sistema lo traduce ademas a la navegacion «atras»
     * (SystemNavigationManager.BackRequested). Si la aplicacion no marca ese evento como
     * atendido, el sistema hace lo suyo por defecto -- CERRARLA. SDL ya tiene el manejador
     * registrado, pero solo marca el evento si se le pide con este hint.
     *
     * Esto NO le quita el boton al juego: la pulsacion del mando llega por otro camino
     * (Windows.Gaming.Input -> SDL_GameController), asi que B sigue frenando y retrocediendo en
     * los menus. Lo unico que deja de significar es «cierra la aplicacion».
     *
     * Con prioridad OVERRIDE para que nada dentro del juego pueda rebajarlo, y aqui, antes de
     * SDL_WinRTRunApp, que es donde SDL registra el manejador.
     *
     * Salir del juego queda donde corresponde en una consola: el boton Xbox. */
    SDL_SetHintWithPriority(SDL_HINT_WINRT_HANDLE_BACK_BUTTON, "1", SDL_HINT_OVERRIDE);

    return SDL_WinRTRunApp(mdkr_uwp_arranque, NULL);
}
