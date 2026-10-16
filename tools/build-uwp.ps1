<#
  Carga el entorno «store» de Visual Studio y lanza la construcción UWP de Diddy Kong Racing.

  «store» y no «desktop»: INCLUDE apunta a las cabeceras que filtran por WINAPI_FAMILY, y LIB a
  las bibliotecas del CRT para App Container, que son las que la Xbox acepta. Sin esto, clang con
  --target=x86_64-pc-windows-msvc encuentra el CRT de escritorio y el binario que sale no pasa la
  validación del paquete: instala, pero la consola responde «Failed to launch the application».

  Este script no compila nada por su cuenta: prepara el entorno y le pasa el trabajo a
  tools/build_uwp.py, que es donde está la receta y los comentarios de cada decisión.

    -Raiz       raíz del árbol de Golden Balloon, ya parcheado con tools/apply_uwp.py
    -Toolchain  carpeta bin de llvm-mingw (clang.exe, clang++.exe, ld.lld.exe)
    -Dawn       carpeta x64 de uwp-dep (include y lib de Dawn)
    -Sdl2       raíz de las fuentes de SDL2, ya compilado para WinRT
    -Salida     carpeta de salida (por omisión, <Raiz>\build-uwp)
    -VcVars     vcvarsall.bat de Visual Studio 2022; si no se pasa, se busca con vswhere
    -Enlazar    enlazar si todo compila
    -Python     intérprete de Python 3 (por omisión, el lanzador «py -3»)

  De dónde sale cada dependencia: docs\DEPENDENCIES.md. Paso a paso: docs\INSTALL.es.md §5.

  Uso (con la PowerShell que trae Windows; pwsh 7 también vale):
    powershell -ExecutionPolicy Bypass -File tools\build-uwp.ps1 -Raiz <árbol> -Toolchain <llvm-mingw\bin> `
         -Dawn <uwp-dep\x64> -Sdl2 <SDL2-2.32.10> -Enlazar
#>
param(
    [Parameter(Mandatory)][string]$Raiz,
    [Parameter(Mandatory)][string]$Toolchain,
    [Parameter(Mandatory)][string]$Dawn,
    [Parameter(Mandatory)][string]$Sdl2,
    [string]$Salida = '',
    [string]$VcVars = '',
    [string]$Python = '',
    [switch]$Enlazar
)
$ErrorActionPreference = 'Stop'

# vswhere viene con cualquier Visual Studio 2017+ y está siempre en la misma ruta.
if (-not $VcVars) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $vswhere) {
        $vs = & $vswhere -latest -products * `
                  -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
                  -property installationPath 2>$null | Select-Object -First 1
        if ($vs) { $VcVars = Join-Path $vs 'VC\Auxiliary\Build\vcvarsall.bat' }
    }
}
if (-not $VcVars -or -not (Test-Path -LiteralPath $VcVars)) {
    throw ('no encuentro vcvarsall.bat: pasa -VcVars con su ruta. Hace falta Visual Studio 2022 ' +
           'con las herramientas de C++ y la carga de trabajo de UWP (docs\INSTALL.es.md §1)')
}

$script = Join-Path $PSScriptRoot 'build_uwp.py'
if (-not (Test-Path -LiteralPath $script)) { throw "falta $script" }

# Los pasos de build_uwp.py informan en castellano; sus hijos heredan esto para que un acento no
# levante un UnicodeEncodeError en una consola que no es UTF-8.
$env:PYTHONIOENCODING = 'utf-8:replace'
$env:PYTHONUTF8 = '1'

$py = if ($Python) { "`"$Python`"" } else { 'py -3' }
$args = @(
    "--raiz `"$Raiz`"",
    "--toolchain `"$Toolchain`"",
    "--dawn `"$Dawn`"",
    "--sdl2 `"$Sdl2`""
)
if ($Salida)  { $args += "--salida `"$Salida`"" }
if ($Enlazar) { $args += '--enlazar' }

# vcvarsall deja el entorno puesto solo dentro de SU proceso: por eso las dos órdenes van encadenadas
# en el mismo cmd. Lanzarlas por separado compilaría con el entorno de escritorio sin avisar.
$orden = "`"$VcVars`" x64 store >nul && $py -X utf8 `"$script`" " + ($args -join ' ')
Write-Host "entorno: $VcVars x64 store"
Write-Host ''
& cmd.exe /c $orden
exit $LASTEXITCODE
