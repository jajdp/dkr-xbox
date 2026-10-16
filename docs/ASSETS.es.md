# Los mosaicos del paquete: los pones tú

*(English: [ASSETS.md](ASSETS.md))*

`package/Assets/` está vacía a propósito. Los mosaicos del port real están hechos con la carátula
de *Diddy Kong Racing*, que es de Nintendo y Rare, así que no se distribuyen aquí
([`NOTICE.es.md`](../NOTICE.es.md)).

El empaquetador se detiene con un mensaje claro si falta cualquiera de los nueve, así que no te vas
a enterar en la consola.

## Lo que dibujas tú: cuatro imágenes

Pon estas cuatro en una carpeta tuya, con estos nombres y estas medidas exactas:

| Archivo | Medida | En qué se convierte |
|---|---|---|
| `xbox-sq1.png` | 150 × 150 | El mosaico cuadrado: el cuadro del juego en la biblioteca |
| `xbox-sq2.png` | 300 × 300 | El mismo a 2×. **Es el que se ve casi siempre** |
| `xbox-ss1.png` | 620 × 300 | La pantalla de carga, mientras el juego arranca |
| `xbox-ss2.png` | 1240 × 600 | La misma a 2× |

Y después:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
python tools/make_tiles.py --origen <tu carpeta> --salida <carpeta de mosaicos>
```

Eso copia esas cuatro y deriva las otras cinco de `xbox-sq2.png` (reduciendo con LANCZOS), porque
el manifiesto las exige y nadie quiere dibujar a mano un icono de 24 píxeles:

| Derivado | Medidas | Para qué existe |
|---|---|---|
| `Square44x44Logo` | 44, 88, 24 | El icono pequeño de las listas de aplicaciones |
| `StoreLogo` | 50, 100 | El que pide `<Properties><Logo>` |

## Cuatro cosas que es fácil equivocar

- **Los nombres SIN calificador de escala tienen que existir igual.** El paquete se arma sin
  `resources.pri`, y entonces `makeappx` busca literalmente el nombre que dice el manifiesto, no la
  variante `scale-200`. Por eso están los dos: `Square150x150Logo.png` y
  `Square150x150Logo.scale-200.png`.

- **No hay mosaico ancho, y es deliberado.** `Wide310x150Logo` no se declara en el manifiesto
  porque en modo desarrollador la consola no lo muestra nunca. Declararlo obligaría a mantener dos
  imágenes más que nadie llega a ver.

- **Centra el motivo y déjale margen.** En la consola el mosaico cuadrado se dibuja dentro de un
  marco de 317 × 317; la pantalla de carga va sobre un fondo liso y ocupa como un 9 % de una
  pantalla de 1920 × 1080. Agrandar el arte no lo hace más legible; centrarlo, sí.

- **Fondo transparente si el motivo es un logo recortado**, opaco si es una carátula con marco. El
  manifiesto pone `BackgroundColor="transparent"`, así que lo que sea transparente deja ver el
  color del tema de la consola.

## La lista entera, para tenerla a mano

Estos son los nueve archivos que `package_uwp.py` espera encontrar. Es una lista, no algo que
haya que teclear:

```text
Square150x150Logo.png                              150 x 150
Square150x150Logo.scale-200.png                    300 x 300
SplashScreen.png                                   620 x 300
SplashScreen.scale-200.png                        1240 x 600
Square44x44Logo.png                                 44 x 44
Square44x44Logo.scale-200.png                       88 x 88
Square44x44Logo.targetsize-24_altform-unplated.png  24 x 24
StoreLogo.png                                       50 x 50
StoreLogo.scale-200.png                            100 x 100
```
