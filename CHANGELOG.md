# Changelog

All notable changes to picodev will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.12] - 2026-07-13

### Fixed
- Handle read-only files when removing existing toolchain on Windows with `--force`.
  `shutil.rmtree` now clears read-only attributes before retrying, compatible with
  Python <3.12 (`onerror`) and Python >=3.12 (`onexc`).

### Added
- Support for custom toolchain and SDK locations via `PICO_TOOLCHAIN_PATH` and 
  `PICO_SDK_PATH` environment variables. When set, `picodev build` automatically
  uses these custom paths and adds the toolchain's bin directory to PATH.

## [0.1.10] - 2026-07-13

### Fixed
- Write generated project templates explicitly as UTF-8, preventing project creation
  from failing under the Windows `cp1252` locale.
- Explain that CMake 3.20 or newer must be installed separately instead of implying
  that `picodev install` manages it.

## [0.1.9] - 2026-07-13

### Fixed
- Use the `certifi` CA bundle for toolchain downloads, fixing certificate verification
  failures with Python 3.14 on Windows.
- Remove incomplete `.part` downloads after a network or TLS error.

## [0.1.8] - 2026-07-13

### Fixed
- Rename the internal Python package from `devlab` to `picodev`, so
  `python -m picodev` works and the FPGA-oriented `devlab` namespace remains separate.

### Changed
- Rename `DEVLAB_HOME` and `~/.devlab` to `PICODEV_HOME` and `~/.picodev`.

## [0.1.7] - 2026-07-13

### Added
- `picodev clean` command to safely remove a project's configured build directory.

## [0.1.6] - 2026-07-13

### Changed
- New projects use a flat `main.c` layout and the configurable CMake template.
- The generated CMake minimum version is now 3.20.
- Project support links now point to `UNIT-Electronics-Labs/unit_devlab_pico`.

### Added
- Default board profiles for UNIT Pulsar RP (RP2350) and DualMCU RP (RP2040).

## [0.1.0] - 2026-07-09

### Added
- **Complete rewrite for Raspberry Pi Pico development**
- Renamed from `devlab-fpga` to `picodev` (CLI command: `picodev`)
- Support for Pico SDK 2.0.0 installation
- ARM GCC 13.2.Rel1 toolchain installation for all platforms
- CMake-based build system for Pico projects
- Support for Raspberry Pi Pico, Pico W, and Pico 2
- Automatic UF2 flashing in BOOTSEL mode
- Project templates with blink examples
- Configuration via `picodev.toml` instead of command-line arguments

### Changed
- Migrated from FPGA tools (OSS CAD Suite) to Pico embedded tools
- Build flow now uses CMake + ARM GCC instead of Yosys/nextpnr
- Flash method changed from openFPGALoader to USB mass storage copy
- Project structure adapted for C/C++ embedded development

### Removed
- All FPGA-specific functionality (Yosys, nextpnr, GHDL, openFPGALoader)
- VHDL/Verilog support (replaced with C/C++)
- FPGA board configurations

---

## Previous devlab-fpga releases:

## [0.1.11] - 2026-07-07

### Fixed
- Prefer 7-Zip extraction for the Windows OSS CAD Suite self-extracting archive when `7z.exe` is available, avoiding execution of the downloaded `.exe` on systems where antivirus or App Control blocks it.

## [0.1.10] - 2026-07-07

### Fixed
- Added a 7-Zip fallback for extracting the Windows OSS CAD Suite self-extracting `.exe` when Windows App Control blocks executing the archive.

## [0.1.9] - 2026-07-07

### Fixed
- Isolated standalone GHDL DLL paths to GHDL commands on Windows so `nextpnr-himbaechel` does not load incompatible GHDL/MSYS runtime DLLs.

## [0.1.8] - 2026-07-07

### Added
- **Automatic GHDL installation for Windows**: New `devlab install-ghdl` command to automatically download and install GHDL v6.0.0 (UCRT64 standalone) on Windows
- GHDL binaries are automatically added to PATH when installed via devlab
- Windows VHDL builds use standalone GHDL synthesis to generate intermediate Verilog before running Yosys
- Support for detecting and using standalone GHDL installation on Windows without a Yosys GHDL plugin

### Changed
- Updated error messages to direct Windows users to run `devlab install-ghdl` for VHDL support
- Improved `devlab doctor` output with instructions for installing GHDL on Windows
- Project creation warnings now mention the `install-ghdl` command
- The Windows VHDL flow no longer expects `ghdl_yosys.dll` in the standalone GHDL package

### Fixed
- GHDL environment variables (GHDL_PREFIX) now correctly point to standalone installation on Windows

## [0.1.7] - 2026-07-07

### Fixed
- **Windows VHDL support**: Made GHDL and yosys-ghdl-plugin optional on Windows, as they are not included in the Windows OSS CAD Suite package
- Installation on Windows no longer fails due to missing GHDL components
- `devlab doctor` now correctly shows GHDL tools as optional on Windows with a note about VHDL support
- Clear error messages when attempting to build VHDL projects on Windows without GHDL installed

### Changed
- `devlab doctor` output improved to show platform-specific tool requirements
- VHDL project creation on Windows now shows a warning about the need for separate GHDL installation
- Better error messages directing users to install GHDL separately on Windows if VHDL support is needed

## [0.1.6] - 2026-07-06

### Added
- Initial release with OSS CAD Suite integration
- Support for Gowin, iCE40, and ECP5 FPGA families
- Verilog and VHDL project templates
- Build and flash commands
- Cross-platform support (Linux, macOS, Windows)
