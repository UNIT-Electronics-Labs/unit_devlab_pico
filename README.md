# picodev

`picodev` is a Python CLI package for Raspberry Pi Pico development. It installs the
Pico SDK and ARM GCC toolchain for the current operating system, creates Pico C/C++
projects, and runs build/flash commands from `picodev.toml`.

## Install

```bash
pip install picodev
```

For local development from this repository:

```bash
pip install -e .
```

## Commands

```bash
picodev doctor
picodev install
picodev new blink
picodev new hello-world
cd blink
picodev build
picodev flash
```

`picodev install` downloads the Pico SDK and ARM GCC toolchain. The installer selects 
the correct toolchain for:

- Linux x64
- Linux arm64  
- macOS x64
- macOS arm64
- Windows x64

The default install location is `~/.devlab`. Set `DEVLAB_HOME` to use a
different directory.

`picodev build` and `picodev flash` automatically run with the installed Pico SDK 
and ARM GCC toolchain environment. You do not need to manually configure paths.
`picodev doctor` checks the tools required by the current platform.

The installed tree layout:

```text
~/.devlab/toolchains/pico-sdk-2.0.0/
  pico-sdk/
~/.devlab/toolchains/arm-none-eabi-gcc-13.2.1/
  bin/
  arm-none-eabi/
```

## Pico SDK and Toolchain Sources

Pico SDK: https://github.com/raspberrypi/pico-sdk

ARM GCC: https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads

Downloaded archives are verified with SHA-256 digests.

## Project Format

`picodev new blink` creates a Pico project:

```text
blink/
  picodev.toml
  CMakeLists.txt
  src/main.c
  .gitignore
```

Use `--board pico_w` to create a Pico W project:

```bash
picodev new my-project --board pico_w
```

Default `picodev.toml`:

```toml
[pico]
board = "pico"

[build]
name = "blink"
build_dir = "build"
sources = ["src/main.c"]
```

## Build Flow

`picodev build` uses CMake to compile your Pico project:

1. Configures CMake with Pico SDK path
2. Builds the project with ARM GCC toolchain
3. Generates `.uf2` file for flashing

Example:

```bash
cd blink
picodev build
```

Output will be in `build/blink.uf2`.

## Flashing

`picodev flash` copies the UF2 file to your Pico in BOOTSEL mode:

1. Hold the BOOTSEL button on your Pico
2. Connect USB cable
3. Release BOOTSEL button
4. Run `picodev flash`

The Pico will appear as a USB mass storage device (RPI-RP2). The flash command
automatically detects the mount point and copies the UF2 file.

```bash
devlab flash
```

To detect if your Pico is in BOOTSEL mode:

```bash
picodev flash --detect
```

## Supported Boards

- `pico` - Raspberry Pi Pico (RP2040)
- `pico_w` - Raspberry Pi Pico W (RP2040 with WiFi)
- `pico2` - Raspberry Pi Pico 2 (RP2350)

## Example Project

Default blink project (`main.c`):

```c
#include <stdio.h>
#include "pico/stdlib.h"

int main() {
    stdio_init_all();
    
    const uint LED_PIN = 25;
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    while (true) {
        gpio_put(LED_PIN, 1);
        sleep_ms(500);
        gpio_put(LED_PIN, 0);
        sleep_ms(500);
    }
}
```

For Pico W, the LED control uses the CYW43 wireless chip:

```c
#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

int main() {
    stdio_init_all();
    
    if (cyw43_arch_init()) {
        printf("Wi-Fi init failed\n");
        return -1;
    }

    while (true) {
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 1);
        sleep_ms(500);
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 0);
        sleep_ms(500);
    }
}
```

## Development Workflow

1. Install toolchains:
   ```bash
   picodev install
   ```

2. Create a project:
   ```bash
   picodev new my-project
   cd my-project
   ```

3. Edit `src/main.c` with your code

4. Build:
   ```bash
   picodev build
   ```

5. Flash to Pico (hold BOOTSEL button):
   ```bash
   picodev flash
   ```

6. Your code runs immediately after flashing!

## Requirements

- Python 3.9+
- CMake (install separately)
- Ninja on Windows (installed by `picodev install`)
- Git (optional, for submodule initialization)

On Ubuntu/Debian:
```bash
sudo apt install cmake git
```

On macOS:
```bash
brew install cmake git
```

On Windows:
Download CMake from https://cmake.org/download/

## License

MIT
