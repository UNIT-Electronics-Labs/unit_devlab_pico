from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import PicodevError
from .toolchain import (
    env_with_toolchain,
    find_executable,
    find_ninja,
    gcc_install_path,
    pico_sdk_install_path,
    missing_toolchain_components,
)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG = "picodev.toml"
SUPPORTED_BOARDS = ("pico", "pico_w", "pico2", "pulsar_rp", "dualmcu_rp")


@dataclass
class BuildConfig:
    """Configuration for a Pico project."""
    project_name: str = "pico_project"
    board: str = "pico"
    build_dir: str = "build"
    sources: list[str] = field(default_factory=lambda: ["main.c"])
    include_dirs: list[str] = field(default_factory=list)
    cmake_args: list[str] = field(default_factory=list)
    
    @property
    def artifact(self) -> str:
        """Get path to the built UF2 file."""
        return f"{self.build_dir}/{self.project_name}.uf2"
    
    @property
    def elf_artifact(self) -> str:
        """Get path to the built ELF file."""
        return f"{self.build_dir}/{self.project_name}.elf"


def load_config(path: Path | None = None) -> BuildConfig:
    """Load project configuration from picodev.toml."""
    config_path = path or Path(DEFAULT_CONFIG)
    if not config_path.exists():
        raise PicodevError(f"Project config not found: {config_path}")

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    pico = _section(data, "pico")
    build = _section(data, "build")

    return BuildConfig(
        project_name=str(build.get("name", "pico_project")),
        board=str(pico.get("board", "pico")),
        build_dir=str(build.get("build_dir", "build")),
        sources=[str(item) for item in build.get("sources", ["main.c"])],
        include_dirs=[str(item) for item in build.get("include_dirs", [])],
        cmake_args=[str(item) for item in build.get("cmake_args", [])],
    )


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    """Get a section from config data, return empty dict if not found."""
    section = data.get(name, {})
    if not isinstance(section, dict):
        raise PicodevError(f"[{name}] must be a table in picodev.toml")
    return section


def create_project(
    name: str,
    directory: Path | None = None,
    force: bool = False,
    board: str = "pico",
) -> Path:
    """Create a new Pico project."""
    if board not in SUPPORTED_BOARDS:
        supported = ", ".join(SUPPORTED_BOARDS)
        raise PicodevError(f"Unsupported board: {board}. Supported boards: {supported}.")

    root = directory or Path(name)
    if root.exists() and any(root.iterdir()) and not force:
        raise PicodevError(f"Directory is not empty: {root}")

    root.mkdir(parents=True, exist_ok=True)
    _write(root / "picodev.toml", _template_config(name, board), force)
    _write(root / "CMakeLists.txt", _template_cmakelists(name, board), force)
    _write(root / "pico_sdk_import.cmake", _template_pico_sdk_import(), force)
    _write(root / "main.c", _template_main_c(board), force)
    _write(root / ".gitignore", "build/\n.vscode/\n", force)
    
    return root


def _write(path: Path, content: str, force: bool) -> None:
    """Write content to file."""
    if path.exists() and not force:
        return
    path.write_text(content)


def build_project(config_path: Path | None = None, dry_run: bool = False) -> Path:
    """Build a Pico project using CMake."""
    config = load_config(config_path)
    project_dir = (config_path.parent if config_path else Path.cwd()).resolve()
    build_dir = (project_dir / config.build_dir).resolve()
    
    # Check for required tools
    missing = missing_toolchain_components()
    if missing:
        raise PicodevError(
            f"Missing required tools: {', '.join(missing)}. "
            "Run 'picodev install' to install toolchains."
        )
    
    # Configure with CMake
    sdk_path = pico_sdk_install_path()
    gcc_path = gcc_install_path()
    env = env_with_toolchain(gcc_path, sdk_path)
    
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine board-specific flags
    board_def = _get_board_definition(config.board)
    
    cmake_configure_cmd = [
        "cmake",
        "-S", str(project_dir),
        "-B", str(build_dir),
        *(["-G", "Ninja"] if sys.platform.startswith("win") else []),
        f"-DPICO_SDK_PATH={sdk_path}",
        f"-DPICO_BOARD={board_def}",
        *(
            [f"-Dpicotool_DIR={env['picotool_DIR']}"]
            if sys.platform.startswith("win") and "picotool_DIR" in env
            else []
        ),
        *config.cmake_args,
    ]
    
    if not dry_run:
        print(f"Configuring CMake project in {build_dir}...")
        _run_command(cmake_configure_cmd, cwd=project_dir, env=env)
    else:
        print(f"Would run: {' '.join(shlex.quote(str(arg)) for arg in cmake_configure_cmd)}")
    
    # Build with CMake
    cmake_build_cmd = ["cmake", "--build", str(build_dir)]
    
    if not dry_run:
        print(f"Building project...")
        _run_command(cmake_build_cmd, cwd=project_dir, env=env)
    else:
        print(f"Would run: {' '.join(shlex.quote(str(arg)) for arg in cmake_build_cmd)}")
    
    artifact = project_dir / config.artifact
    if not dry_run and not artifact.exists():
        raise PicodevError(f"Build completed but artifact not found: {artifact}")
    
    return artifact


def clean_project(config_path: Path | None = None) -> tuple[Path, bool]:
    """Remove the configured build directory for a Pico project."""
    config_path = config_path or Path(DEFAULT_CONFIG)
    config = load_config(config_path)
    project_dir = config_path.parent.resolve()
    build_dir = (project_dir / config.build_dir).resolve()

    try:
        build_dir.relative_to(project_dir)
    except ValueError as exc:
        raise PicodevError(
            f"Refusing to clean a build directory outside the project: {build_dir}"
        ) from exc

    if build_dir == project_dir:
        raise PicodevError("Refusing to clean the project root directory.")

    if not build_dir.exists():
        return build_dir, False
    if not build_dir.is_dir():
        raise PicodevError(f"Build path is not a directory: {build_dir}")

    shutil.rmtree(build_dir)
    return build_dir, True


def _get_board_definition(board: str) -> str:
    """Get the board definition for CMake."""
    board_map = {
        "pico": "pico",
        "pico_w": "pico_w",
        "pico2": "pico2",
        "pulsar_rp": "pico2",
        "dualmcu_rp": "pico",
    }
    return board_map.get(board, "pico")


def flash_project(
    config_path: Path | None = None,
    artifact: Path | None = None,
    probe: str | None = None,
    dry_run: bool = False,
) -> None:
    """Flash the project ELF over SWD using pyOCD."""
    config_path = config_path or Path(DEFAULT_CONFIG)
    config = load_config(config_path)
    project_dir = config_path.parent.resolve()

    firmware = artifact or Path(config.elf_artifact)
    if not firmware.is_absolute():
        firmware = project_dir / firmware
    firmware = firmware.resolve()

    if not dry_run and not firmware.exists():
        raise PicodevError(f"ELF firmware not found: {firmware}. Run 'picodev build' first.")

    target = "rp2350" if config.board in {"pico2", "pulsar_rp"} else "rp2040"
    command = [sys.executable, "-m", "pyocd", "flash", "--target", target]
    if probe:
        command.extend(["--probe", probe])
    command.append(str(firmware))

    if dry_run:
        print(f"Would run: {' '.join(shlex.quote(str(arg)) for arg in command)}")
        return

    print(f"Flashing {firmware} to {target} with pyOCD...")
    _run_command(command, cwd=project_dir)
    print("Flash complete! Target reset and running.")


def _find_pico_mount() -> Path | None:
    """Find Pico mount point in BOOTSEL mode."""
    import platform
    
    system = platform.system()
    
    if system == "Linux":
        # Check common mount points
        candidates = [
            Path("/media") / Path.home().name / "RPI-RP2",
            Path("/run/media") / Path.home().name / "RPI-RP2",
            Path("/mnt/RPI-RP2"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
    
    elif system == "Darwin":  # macOS
        return Path("/Volumes/RPI-RP2") if Path("/Volumes/RPI-RP2").exists() else None
    
    elif system == "Windows":
        # Check drive letters D: through Z:
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            candidate = Path(f"{letter}:/")
            if candidate.exists() and (candidate / "INFO_UF2.TXT").exists():
                return candidate
    
    return None


def detect_flash(dry_run: bool = False) -> None:
    """List debug probes available to pyOCD."""
    command = [sys.executable, "-m", "pyocd", "list", "--probes"]
    if dry_run:
        print(f"Would run: {' '.join(shlex.quote(str(arg)) for arg in command)}")
    else:
        _run_command(command)


def doctor(strict: bool = False) -> int:
    """Check for required tools."""
    missing = missing_toolchain_components()
    
    if not missing:
        print("✓ All required tools are available")
        print(f"  - ARM GCC: {find_executable('arm-none-eabi-gcc')}")
        print(f"  - Pico SDK: {pico_sdk_install_path()}")
        print(f"  - CMake: {shutil.which('cmake')}")
        if sys.platform.startswith("win"):
            print(f"  - Ninja: {find_ninja()}")
        return 0
    
    print("Missing tools:")
    for tool in missing:
        print(f"  ✗ {tool}")
    
    print("\nRun 'picodev install' to install missing toolchains.")
    
    return 1 if strict else 0


def _run_command(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    """Run a command and check for errors."""
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env)
    except subprocess.CalledProcessError as exc:
        raise PicodevError(
            f"Command failed with exit code {exc.returncode}: {' '.join(cmd)}"
        ) from exc
    except OSError as exc:
        raise PicodevError(f"Failed to run command: {exc}") from exc


def _template_config(name: str, board: str) -> str:
    """Generate picodev.toml template."""
    return f"""[pico]
board = "{board}"

[build]
name = "{name}"
build_dir = "build"
sources = ["main.c"]
"""


def _template_cmakelists(name: str, board: str) -> str:
    """Generate CMakeLists.txt template."""
    board_lib = "\n    pico_cyw43_arch_none" if board == "pico_w" else ""
    cmake_board = _get_board_definition(board)

    return f"""cmake_minimum_required(VERSION 3.20)

include(pico_sdk_import.cmake)

# ─────────────────────────────────────────────
# PROJECT CONFIGURATION
# Automatically generated by picodev
# ─────────────────────────────────────────────
set(PROJECT_NAME    "{name}")
set(PROJECT_SOURCES "main.c")
set(PICO_BOARD      "{cmake_board}")

set(PROJECT_LIBS
    pico_stdlib
    hardware_gpio{board_lib}
)
# ─────────────────────────────────────────────
# DO NOT MODIFY BELOW THIS LINE
# ─────────────────────────────────────────────

project(${{PROJECT_NAME}} C CXX ASM)

pico_sdk_init()

add_executable(${{PROJECT_NAME}} ${{PROJECT_SOURCES}})

target_link_libraries(${{PROJECT_NAME}} ${{PROJECT_LIBS}})

pico_add_extra_outputs(${{PROJECT_NAME}})

pico_enable_stdio_usb(${{PROJECT_NAME}} 1)
pico_enable_stdio_uart(${{PROJECT_NAME}} 0)
"""


def _template_pico_sdk_import() -> str:
    """Generate a local Pico SDK import shim for the managed SDK."""
    return """if(NOT DEFINED ENV{PICO_SDK_PATH})
    message(FATAL_ERROR "PICO_SDK_PATH is not set. Run the build with 'picodev build'.")
endif()

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
"""


def _template_main_c(board: str) -> str:
    """Generate main.c template."""
    if board == "pico_w":
        return """#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

int main() {
    stdio_init_all();
    
    if (cyw43_arch_init()) {
        printf("Wi-Fi init failed\\n");
        return -1;
    }

    while (true) {
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 1);
        sleep_ms(500);
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 0);
        sleep_ms(500);
    }
}
"""
    else:
        return """#include <stdio.h>
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
"""
