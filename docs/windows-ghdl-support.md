# Soporte VHDL/GHDL en Windows

Esta guia cubre la instalacion y verificacion de `devlab` con soporte VHDL en
Windows. En Windows, OSS CAD Suite no incluye GHDL, por eso `devlab` instala
GHDL como paquete separado y lo usa solo para convertir VHDL a Verilog antes de
ejecutar Yosys.

## Actualizar devlab

Mientras la version nueva no este publicada en PyPI, instala desde GitHub:

```powershell
python -m pip install --upgrade git+https://github.com/UNIT-Electronics-Labs/unit_devlab_lib.git
```

Verifica que estes usando la version con el hotfix de Windows:

```powershell
devlab --version
```

La version esperada es:

```text
devlab 0.1.11
```

Los ejemplos usan `devlab`. Si el comando no esta en `PATH`, usa
`python -m devlab` con los mismos argumentos, por ejemplo:

```powershell
python -m devlab install
```

## Instalar las herramientas

Instala o actualiza OSS CAD Suite:

```powershell
devlab install
```

Si Windows App Control bloquea el `.exe` autoextraible de OSS CAD Suite,
instala 7-Zip y vuelve a ejecutar el instalador. `devlab` usara `7z` como
fallback para extraer el archivo sin ejecutarlo:

```powershell
winget install 7zip.7zip
devlab install --force
```

Instala GHDL standalone para Windows:

```powershell
devlab install-ghdl
```

El comando descarga `ghdl-mcode-6.0.0-ucrt64.zip` y lo instala en:

```text
C:\Users\<usuario>\.devlab\toolchains\ghdl-6.0.0-windows-x64
```

## Verificar el entorno

Ejecuta:

```powershell
devlab doctor
```

En Windows, `devlab doctor` debe encontrar las herramientas de OSS CAD Suite.
GHDL solo es requerido si vas a compilar proyectos VHDL.

## Crear un proyecto VHDL

```powershell
devlab new blink-vhdl --hdl vhdl
cd blink-vhdl
devlab build --dry-run
```

El `dry-run` debe mostrar una primera etapa con GHDL similar a:

```powershell
ghdl --synth --std=08 --out=verilog src/top.vhd -e top > build/top_ghdl.v
```

Despues debe mostrar Yosys usando el Verilog generado:

```powershell
yosys -p "synth_gowin -top top -json build/top.json" build/top_ghdl.v
```

Para compilar realmente:

```powershell
devlab build
```

## Flujo interno en Windows

El flujo VHDL en Windows es:

```text
VHDL sources
  -> ghdl --synth --out=verilog
  -> build/<top>_ghdl.v
  -> yosys
  -> nextpnr-himbaechel
  -> gowin_pack
```

No se usa `yosys-ghdl` en Windows. El paquete `ghdl-mcode-6.0.0-ucrt64.zip`
incluye `ghdl.exe` y las librerias de GHDL, pero no incluye un plugin
`ghdl_yosys.dll`.

## Antivirus durante build y flash

`devlab build` y `devlab flash` ejecutan binarios de OSS CAD Suite. En Gowin,
los procesos principales son:

```text
yosys.exe
nextpnr-himbaechel.exe
gowin_pack.exe
openFPGALoader.exe
```

Para VHDL tambien se ejecuta:

```text
ghdl.exe
```

`devlab` no puede firmar esos ejecutables porque pertenecen a OSS CAD Suite y
GHDL. Firmarlos de verdad requiere un certificado Authenticode y un paquete
propio firmado. Lo que si se puede hacer es verificar que los archivos vienen
del release esperado y agregar exclusiones minimas en Defender.

### Verificar el paquete descargado

`devlab install` verifica automaticamente el SHA-256 del archivo OSS CAD Suite.
Tambien puedes comprobarlo manualmente:

```powershell
Get-FileHash "$env:USERPROFILE\.devlab\cache\oss-cad-suite-windows-x64-20260706.exe" -Algorithm SHA256
```

El SHA-256 esperado para ese release es:

```text
E8AB814D490D89163E418DC634842CF086EA305DDE0C32F832528194A5B93AC9
```

### Agregar exclusiones minimas en Defender

Ejecuta PowerShell como Administrador y agrega exclusiones por proceso:

```powershell
$oss="$env:USERPROFILE\.devlab\toolchains\oss-cad-suite-2026-07-06-windows-x64\oss-cad-suite\bin"
$ghdl="$env:USERPROFILE\.devlab\toolchains\ghdl-6.0.0-windows-x64\bin"

Add-MpPreference -ExclusionProcess "$oss\yosys.exe"
Add-MpPreference -ExclusionProcess "$oss\nextpnr-himbaechel.exe"
Add-MpPreference -ExclusionProcess "$oss\gowin_pack.exe"
Add-MpPreference -ExclusionProcess "$oss\openFPGALoader.exe"
Add-MpPreference -ExclusionProcess "$ghdl\ghdl.exe"
```

Si Defender sigue bloqueando DLLs o archivos temporales, usa una exclusion de
carpeta limitada solo al directorio de herramientas:

```powershell
Add-MpPreference -ExclusionPath "$env:USERPROFILE\.devlab"
```

Evita apagar la proteccion global de Windows. Las exclusiones anteriores son
mas acotadas y reproducibles.

## Solucion de problemas

### `devlab --version` no muestra `0.1.11`

Actualiza desde GitHub:

```powershell
python -m pip install --upgrade git+https://github.com/UNIT-Electronics-Labs/unit_devlab_lib.git
```

Si tienes varios Python instalados, verifica desde cual estas ejecutando
`devlab`:

```powershell
where devlab
python -m pip show devlab-fpga
```

### Windows App Control bloquea OSS CAD Suite

Si `devlab install` falla con:

```text
WinError 4551
Una directiva de Control de aplicaciones bloqueo este archivo
```

Windows bloqueo la ejecucion del `.exe` autoextraible de OSS CAD Suite.
Instala 7-Zip y fuerza la reinstalacion:

```powershell
winget install 7zip.7zip
devlab install --force
```

`devlab 0.1.11` o superior usa `7z.exe` primero cuando esta disponible, para
extraer el archivo sin ejecutar el `.exe`. Si no usas `winget`, instala 7-Zip desde
https://www.7-zip.org/ y confirma que `7z.exe` este en `PATH` o en
`C:\Program Files\7-Zip`.

Si el antivirus aun bloquea el archivo al descargarlo o leerlo como archivo
comprimido, evita apagar la proteccion globalmente. Agrega una exclusion solo
para el directorio de herramientas de `devlab`:

```powershell
Add-MpPreference -ExclusionPath "$env:USERPROFILE\.devlab"
```

Despues repite:

```powershell
devlab install --force
```

### Falta GHDL

Ejecuta:

```powershell
devlab install-ghdl
devlab doctor
```

### `nextpnr-himbaechel.exe` falla con `3221225785`

Ese codigo suele indicar una DLL incompatible. Actualiza a `devlab 0.1.9` o
superior:

```powershell
python -m pip install --upgrade git+https://github.com/UNIT-Electronics-Labs/unit_devlab_lib.git
devlab --version
```

Desde `0.1.9`, `devlab` solo agrega las DLLs de GHDL cuando ejecuta `ghdl`.
`nextpnr-himbaechel.exe` corre con el entorno limpio de OSS CAD Suite.

### Error de pines sin restricciones

Si el build llega a `nextpnr` y falla con un mensaje como:

```text
ERROR: Unconstrained IO
```

GHDL y Yosys ya funcionaron. Actualiza `pins.cst` con los pines reales de tu
tarjeta.

## Comandos rapidos

```powershell
python -m pip install --upgrade git+https://github.com/UNIT-Electronics-Labs/unit_devlab_lib.git
devlab --version
winget install 7zip.7zip
devlab install
devlab install-ghdl
devlab doctor
devlab new blink-vhdl --hdl vhdl
cd blink-vhdl
devlab build --dry-run
devlab build
```
