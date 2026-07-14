from __future__ import annotations

import argparse
import platform
from pathlib import Path

from . import __version__
from .errors import PicodevError
from .platforms import current_platform
from .project import (
    SUPPORTED_BOARDS,
    build_project,
    clean_project,
    create_project,
    detect_flash,
    doctor,
    flash_project,
)
from .toolchain import (
    ARM_GCC_VERSION,
    ARM_GCC_RELEASE_URL,
    NINJA_RELEASE_URL,
    NINJA_VERSION,
    PICOTOOL_RELEASE_URL,
    PICOTOOL_VERSION,
    PICO_SDK_VERSION,
    PICO_SDK_RELEASE_URL,
    gcc_archive_path,
    gcc_install_path,
    pico_sdk_install_path,
    picodev_home,
    install_toolchains,
    ninja_install_path,
    picotool_install_path,
    select_asset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="picodev",
        description="Install Pico SDK toolchains and run Raspberry Pi Pico build flows.",
    )
    parser.add_argument("--version", action="version", version=f"picodev {__version__}")

    commands = parser.add_subparsers(dest="command")

    doctor_parser = commands.add_parser("doctor", help="Check local Pico development tools.")
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when a tool is missing.",
    )
    doctor_parser.set_defaults(func=_doctor)

    install_parser = commands.add_parser(
        "install", help="Install Pico SDK, ARM GCC, Ninja, and picotool."
    )
    install_parser.add_argument("--force", action="store_true", help="Re-download and reinstall.")
    install_parser.set_defaults(func=_install)

    new_parser = commands.add_parser("new", help="Create a new Pico project.")
    new_parser.add_argument("name", help="Project directory name.")
    new_parser.add_argument("--dir", type=Path, help="Target directory. Defaults to NAME.")
    new_parser.add_argument("--force", action="store_true", help="Overwrite template files.")
    new_parser.add_argument(
        "--board",
        choices=SUPPORTED_BOARDS,
        default="pico",
        help="Target board. Defaults to pico.",
    )
    new_parser.set_defaults(func=_new)

    build = commands.add_parser("build", help="Build the current Pico project.")
    build.add_argument("-c", "--config", type=Path, help="Path to picodev.toml.")
    build.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running them.",
    )
    build.set_defaults(func=_build)

    clean = commands.add_parser("clean", help="Remove the current project's build directory.")
    clean.add_argument("-c", "--config", type=Path, help="Path to picodev.toml.")
    clean.set_defaults(func=_clean)

    flash = commands.add_parser("flash", help="Flash the built ELF to Pico using pyOCD.")
    flash.add_argument("-c", "--config", type=Path, help="Path to picodev.toml.")
    flash.add_argument("--artifact", type=Path, help="ELF firmware path.")
    flash.add_argument("--probe", help="pyOCD debug probe unique ID or prefix.")
    flash.add_argument(
        "--detect",
        action="store_true",
        help="List debug probes detected by pyOCD without flashing.",
    )
    flash.add_argument("--dry-run", action="store_true", help="Print command without running it.")
    flash.set_defaults(func=_flash)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.error("the following arguments are required: command")
        return args.func(args)
    except PicodevError as exc:
        parser.exit(2, f"picodev: error: {exc}\n")


def _doctor(args: argparse.Namespace) -> int:
    platform_id = current_platform()
    asset = select_asset(platform_id)
    print(f"picodev: {__version__}")
    print(f"python: {platform.python_version()} ({platform.python_implementation()})")
    print(f"platform: {platform_id.key}")
    print(f"home: {picodev_home()}")
    print(f"pico-sdk: {PICO_SDK_VERSION} ({PICO_SDK_RELEASE_URL})")
    print(f"arm-gcc: {ARM_GCC_VERSION} ({ARM_GCC_RELEASE_URL})")
    print(f"ninja: {NINJA_VERSION} ({NINJA_RELEASE_URL})")
    print(f"picotool: {PICOTOOL_VERSION} ({PICOTOOL_RELEASE_URL})")
    print(f"asset: {asset.name}")
    print(f"gcc-archive: {gcc_archive_path(asset)}")
    print(f"gcc-toolchain: {gcc_install_path(asset)}")
    print(f"pico-sdk-path: {pico_sdk_install_path()}")
    if platform_id.os_name == "windows":
        print(f"ninja-path: {ninja_install_path()}")
        print(f"picotool-path: {picotool_install_path()}")
    print()
    return doctor(strict=args.strict)


def _install(args: argparse.Namespace) -> int:
    gcc_path, sdk_path, ninja_path, picotool_path = install_toolchains(force=args.force)
    print(f"\n✓ ARM GCC toolchain installed at {gcc_path}")
    print(f"✓ Pico SDK installed at {sdk_path}")
    if ninja_path:
        print(f"✓ Ninja installed at {ninja_path}")
    if picotool_path:
        print(f"✓ picotool installed at {picotool_path}")
    print("\nToolchains are ready! Run 'picodev new <project>' to create a project.")
    return 0


def _new(args: argparse.Namespace) -> int:
    root = create_project(args.name, directory=args.dir, force=args.force, board=args.board)
    print(f"Created Pico project at {root}")
    print(f"\nNext steps:")
    print(f"  cd {root}")
    print(f"  picodev build")
    print(f"  picodev flash")
    return 0


def _build(args: argparse.Namespace) -> int:
    artifact = build_project(config_path=args.config, dry_run=args.dry_run)
    print(f"\n✓ Build artifact: {artifact}")
    return 0


def _clean(args: argparse.Namespace) -> int:
    build_dir, removed = clean_project(config_path=args.config)
    if removed:
        print(f"Cleaned build directory: {build_dir}")
    else:
        print(f"Build directory is already clean: {build_dir}")
    return 0


def _flash(args: argparse.Namespace) -> int:
    if args.detect:
        detect_flash(dry_run=args.dry_run)
        return 0

    flash_project(
        config_path=args.config,
        artifact=args.artifact,
        probe=args.probe,
        dry_run=args.dry_run,
    )
    return 0
