# Installing CMake

`picodev` requires CMake 3.20 or newer to configure and build Raspberry Pi Pico
projects. CMake is a system prerequisite and is not installed by
`picodev install`.

After installing CMake, open a new terminal and verify the installation:

```text
cmake --version
python -m picodev doctor
```

The first command must report CMake 3.20 or newer, and `picodev doctor` should
no longer list `cmake` under `Missing tools`.

## Windows

### Option 1: WinGet (recommended)

Open PowerShell and run:

```powershell
winget install --exact --id Kitware.CMake --source winget
```

Close PowerShell, open a new PowerShell window, and verify:

```powershell
cmake --version
python -m picodev doctor
```

The new window is important: a PowerShell process that was already open before
the installation keeps its old `PATH` value. `picodev` also checks CMake's
standard `C:\Program Files\CMake\bin` location as a fallback.

WinGet is provided through App Installer on current Windows 10 and Windows 11
systems. If `winget` is not recognized, install or update **App Installer** from
the Microsoft Store.

### Option 2: Official installer

1. Open the [official CMake download page](https://cmake.org/download/).
2. Download the Windows x64 installer (`.msi`).
3. Run the installer and select an option that adds CMake to `PATH`.
4. Open a new PowerShell window and run `cmake --version`.

### Windows troubleshooting

If CMake is installed but PowerShell still reports that `cmake` is not
recognized, check whether it is discoverable:

```powershell
Get-Command cmake -ErrorAction SilentlyContinue
Test-Path 'C:\Program Files\CMake\bin\cmake.exe'
```

If the second command returns `True`, add `C:\Program Files\CMake\bin` to the
user or system `PATH`, then open a new terminal. Do not add the path only to the
current PowerShell session, because `picodev` must be able to find it in future
terminals too.

## Ubuntu and Debian

```bash
sudo apt update
sudo apt install cmake
cmake --version
python -m picodev doctor
```

Ubuntu 22.04 LTS and newer provide a CMake version that satisfies the minimum
3.20 requirement. On an older distribution, use a newer distribution release
or an installer from the [official CMake download page](https://cmake.org/download/).

## macOS

With [Homebrew](https://brew.sh/) installed:

```bash
brew install cmake
cmake --version
python -m picodev doctor
```

## Continue with picodev

Once `picodev doctor` finds CMake, create and build a project:

```text
python -m picodev new blink
cd blink
python -m picodev build
```

If a previous `picodev new` attempt left a partially created directory, remove
that directory or explicitly overwrite its template files:

```text
python -m picodev new blink --force
```

If CMake previously failed with `No CMAKE_C_COMPILER could be found`, clear its
incomplete cache before retrying with an updated `picodev` installation:

```text
python -m picodev clean
python -m picodev build
```

`picodev` passes its managed ARM GCC installation to the Pico SDK through
`PICO_TOOLCHAIN_PATH`; no separate ARM compiler installation is required.

With `picodev 0.1.10`, set the variable manually in PowerShell before cleaning
and rebuilding:

```powershell
$env:PICO_TOOLCHAIN_PATH = "$env:USERPROFILE\.picodev\toolchains\arm-gcc-13.2.Rel1-windows-x64"
python -m picodev clean
python -m picodev build
```

The configure command printed after upgrading `picodev` should contain a
`-DPICO_TOOLCHAIN_PATH=...` argument. If it does not, the older package is still
being executed.

## References

- [CMake downloads](https://cmake.org/download/)
- [Microsoft WinGet documentation](https://learn.microsoft.com/windows/package-manager/winget/)
- [Homebrew CMake formula](https://formulae.brew.sh/formula/cmake)
- [Ubuntu CMake packages](https://packages.ubuntu.com/search?keywords=cmake)
