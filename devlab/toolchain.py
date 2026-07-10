from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .errors import DevlabError
from .platforms import PlatformId, current_platform


# Pico SDK version and release info
PICO_SDK_VERSION = "2.0.0"
PICO_SDK_RELEASE_URL = "https://github.com/raspberrypi/pico-sdk/releases/tag/2.0.0"

# ARM GCC Toolchain version
ARM_GCC_VERSION = "13.2.Rel1"
ARM_GCC_RELEASE_URL = "https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads"


@dataclass(frozen=True)
class ToolchainAsset:
    platform: str
    name: str
    url: str
    sha256: str | None = None

    @property
    def suffix(self) -> str:
        return Path(self.name).suffix


# ARM GCC Toolchain assets for different platforms
ARM_GCC_ASSETS: dict[str, ToolchainAsset] = {
    "linux-x64": ToolchainAsset(
        platform="linux-x64",
        name="arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz",
        url="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz",
        sha256="6cd1bbc1d9ae57312bcd169ae283153a9572bd6a8e4eeae2fedfbc33b115fdbb",
    ),
    "linux-arm64": ToolchainAsset(
        platform="linux-arm64",
        name="arm-gnu-toolchain-13.2.rel1-aarch64-arm-none-eabi.tar.xz",
        url="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-aarch64-arm-none-eabi.tar.xz",
        sha256="8fd8b4a0a8d44ab2e195ccfbeef42223dfb3ede29d80f14dcf2183c34b8d199a",
    ),
    "darwin-x64": ToolchainAsset(
        platform="darwin-x64",
        name="arm-gnu-toolchain-13.2.rel1-darwin-x86_64-arm-none-eabi.tar.xz",
        url="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-darwin-x86_64-arm-none-eabi.tar.xz",
        sha256="075faa4f3e8eb45e59144858202351a28706f54a6ec17eedd88c9fb9412372cc",
    ),
    "darwin-arm64": ToolchainAsset(
        platform="darwin-arm64",
        name="arm-gnu-toolchain-13.2.rel1-darwin-arm64-arm-none-eabi.tar.xz",
        url="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-darwin-arm64-arm-none-eabi.tar.xz",
        sha256="39c44f8af42695b7b871df42e346c09fee670ea8dfc11f17083e296ea2b0d279",
    ),
    "windows-x64": ToolchainAsset(
        platform="windows-x64",
        name="arm-gnu-toolchain-13.2.rel1-mingw-w64-i686-arm-none-eabi.zip",
        url="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-mingw-w64-i686-arm-none-eabi.zip",
        sha256="51d933f00578aa28016c5e3c84f94403274ea7915539f8e56c13e2196437d18f",
    ),
}


# Pico SDK download
PICO_SDK_ASSET = ToolchainAsset(
    platform="all",
    name="pico-sdk-2.0.0.tar.gz",
    url="https://github.com/raspberrypi/pico-sdk/archive/refs/tags/2.0.0.tar.gz",
    sha256=None,  # GitHub generates tarballs dynamically
)


def devlab_home() -> Path:
    return Path(os.environ.get("DEVLAB_HOME", Path.home() / ".devlab")).expanduser()


def toolchains_dir(home: Path | None = None) -> Path:
    return (home or devlab_home()) / "toolchains"


def cache_dir(home: Path | None = None) -> Path:
    return (home or devlab_home()) / "cache"


def select_asset(platform_id: PlatformId | None = None) -> ToolchainAsset:
    """Select ARM GCC toolchain asset for the current platform."""
    platform_id = platform_id or current_platform()
    try:
        return ARM_GCC_ASSETS[platform_id.key]
    except KeyError as exc:
        supported = ", ".join(sorted(ARM_GCC_ASSETS))
        raise DevlabError(
            f"Unsupported platform for ARM GCC toolchain: {platform_id.key}. "
            f"Supported: {supported}"
        ) from exc


def gcc_install_path(asset: ToolchainAsset | None = None, home: Path | None = None) -> Path:
    """Get installation path for ARM GCC toolchain."""
    asset = asset or select_asset()
    return toolchains_dir(home) / f"arm-gcc-{ARM_GCC_VERSION}-{asset.platform}"


def pico_sdk_install_path(home: Path | None = None) -> Path:
    """Get installation path for Pico SDK."""
    return toolchains_dir(home) / f"pico-sdk-{PICO_SDK_VERSION}"


def gcc_archive_path(asset: ToolchainAsset | None = None, home: Path | None = None) -> Path:
    asset = asset or select_asset()
    return cache_dir(home) / asset.name


def pico_sdk_archive_path(home: Path | None = None) -> Path:
    return cache_dir(home) / PICO_SDK_ASSET.name


def gcc_bin_dir(path: Path | None = None) -> Path:
    """Get bin directory for ARM GCC toolchain."""
    path = path or gcc_install_path()
    return path / "bin"


def env_with_toolchain(
    gcc_path: Path | None = None,
    sdk_path: Path | None = None,
) -> dict[str, str]:
    """Create environment with Pico SDK and ARM GCC toolchain paths."""
    gcc_path = gcc_path or gcc_install_path()
    sdk_path = sdk_path or pico_sdk_install_path()
    
    env = os.environ.copy()
    
    # Add ARM GCC to PATH
    binary_dirs = [str(gcc_bin_dir(gcc_path))]
    env["PATH"] = os.pathsep.join(binary_dirs) + os.pathsep + env.get("PATH", "")
    
    # Set Pico SDK environment variables
    env["PICO_SDK_PATH"] = str(sdk_path)
    
    return env


def find_executable(name: str, gcc_path: Path | None = None) -> str | None:
    """Find an executable in the ARM GCC toolchain."""
    suffixes = [""]
    if sys.platform.startswith("win"):
        suffixes = [".exe", ".bat", ".cmd", ""]

    binary_dir = gcc_bin_dir(gcc_path)
    for suffix in suffixes:
        candidate = binary_dir / f"{name}{suffix}"
        if candidate.exists():
            return str(candidate)
    
    return shutil.which(name, path=env_with_toolchain(gcc_path).get("PATH"))


def missing_toolchain_components(
    gcc_path: Path | None = None,
    sdk_path: Path | None = None,
) -> list[str]:
    """Check for missing toolchain components."""
    gcc_path = gcc_path or gcc_install_path()
    sdk_path = sdk_path or pico_sdk_install_path()
    
    missing = []
    
    # Check ARM GCC
    if not find_executable("arm-none-eabi-gcc", gcc_path):
        missing.append("arm-none-eabi-gcc")
    
    # Check Pico SDK
    if not (sdk_path / "pico_sdk_init.cmake").exists():
        missing.append("pico-sdk")
    
    # Check CMake
    if not shutil.which("cmake"):
        missing.append("cmake")

    # CMake uses Ninja explicitly on Windows, avoiding a dependency on NMake
    # and the Visual Studio developer environment.
    if sys.platform.startswith("win") and not shutil.which("ninja"):
        missing.append("ninja")
    
    return missing


def download_asset(asset: ToolchainAsset, destination: Path, force: bool = False) -> Path:
    """Download a toolchain asset."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        if asset.sha256:
            verify_sha256(destination, asset.sha256)
        return destination

    tmp_destination = destination.with_suffix(destination.suffix + ".part")
    if tmp_destination.exists():
        tmp_destination.unlink()

    def report(blocks: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        downloaded = min(blocks * block_size, total_size)
        percent = downloaded * 100 / total_size
        print(f"\rDownloading {asset.name}: {percent:5.1f}%", end="", flush=True)

    try:
        urllib.request.urlretrieve(asset.url, tmp_destination, reporthook=report)
        print()
    except OSError as exc:
        raise DevlabError(f"Could not download {asset.url}: {exc}") from exc

    if asset.sha256:
        verify_sha256(tmp_destination, asset.sha256)
    tmp_destination.replace(destination)
    return destination


def verify_sha256(path: Path, expected: str) -> None:
    """Verify SHA256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise DevlabError(
            f"SHA-256 mismatch for {path.name}: expected {expected}, got {actual}"
        )


def install_arm_gcc(home: Path | None = None, force: bool = False) -> Path:
    """Install ARM GCC toolchain."""
    home = home or devlab_home()
    asset = select_asset()
    destination = gcc_install_path(asset, home)

    if destination.exists() and find_executable("arm-none-eabi-gcc", destination) and not force:
        return destination

    archive = download_asset(asset, gcc_archive_path(asset, home), force=force)

    print(f"Installing ARM GCC toolchain to {destination}...")
    
    if asset.name.endswith(".zip"):
        _extract_zip(archive, destination, force=force)
    elif asset.name.endswith((".tar.xz", ".tar.gz", ".tgz")):
        _extract_tarball(archive, destination, force=force)
    else:
        raise DevlabError(f"Unsupported archive format: {asset.name}")
    
    # Mark executables on Unix-like systems
    _mark_executables(gcc_bin_dir(destination))
    
    # Verify installation
    if not find_executable("arm-none-eabi-gcc", destination):
        raise DevlabError(
            "ARM GCC installation completed but arm-none-eabi-gcc was not found. "
            "Check the installation manually."
        )
    
    return destination


def install_pico_sdk(home: Path | None = None, force: bool = False) -> Path:
    """Install Pico SDK."""
    home = home or devlab_home()
    destination = pico_sdk_install_path(home)

    if destination.exists() and (destination / "pico_sdk_init.cmake").exists() and not force:
        return destination

    archive = download_asset(PICO_SDK_ASSET, pico_sdk_archive_path(home), force=force)

    print(f"Installing Pico SDK to {destination}...")
    _extract_tarball(archive, destination, force=force)
    
    # Initialize submodules by cloning them
    _init_pico_sdk_submodules(destination)
    
    # Verify installation
    if not (destination / "pico_sdk_init.cmake").exists():
        raise DevlabError(
            "Pico SDK installation completed but pico_sdk_init.cmake was not found. "
            "Check the installation manually."
        )
    
    return destination


def _init_pico_sdk_submodules(sdk_path: Path) -> None:
    """Initialize Pico SDK submodules (tinyusb, etc)."""
    print("Initializing Pico SDK submodules...")
    
    # For now, just download tinyusb which is the main submodule needed
    tinyusb_path = sdk_path / "lib" / "tinyusb"
    if not tinyusb_path.exists():
        tinyusb_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.check_call(
                ["git", "clone", "--depth", "1", "--branch", "0.16.0",
                 "https://github.com/hathach/tinyusb.git", str(tinyusb_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            # If git is not available, we'll skip submodule initialization
            print("Warning: Could not initialize tinyusb submodule. Git may not be available.")


def install_toolchains(home: Path | None = None, force: bool = False) -> tuple[Path, Path]:
    """Install both ARM GCC and Pico SDK."""
    gcc_path = install_arm_gcc(home, force)
    sdk_path = install_pico_sdk(home, force)
    return gcc_path, sdk_path


def _move_extracted_tree(source: Path, destination: Path, force: bool) -> None:
    """Move extracted files to destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not force:
            raise DevlabError(f"Install destination already exists: {destination}")
        shutil.rmtree(destination)

    # Find the actual root directory in the extracted files
    items = list(source.iterdir())
    if len(items) == 1 and items[0].is_dir():
        # Single directory extracted, move its contents
        shutil.move(str(items[0]), str(destination))
    else:
        # Multiple items, move all
        destination.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            shutil.move(str(child), destination / child.name)


def _extract_zip(archive: Path, destination: Path, force: bool) -> None:
    """Extract ZIP archive."""
    with tempfile.TemporaryDirectory(prefix="devlab-pico-") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(archive) as zip_file:
            _safe_extract_zip(zip_file, tmp_path)
        _move_extracted_tree(tmp_path, destination, force=force)


def _extract_tarball(archive: Path, destination: Path, force: bool) -> None:
    """Extract tarball (tar.gz, tar.xz, etc)."""
    with tempfile.TemporaryDirectory(prefix="devlab-pico-") as tmp:
        tmp_path = Path(tmp)
        
        # Determine compression type
        if archive.name.endswith(".tar.xz"):
            mode = "r:xz"
        elif archive.name.endswith((".tar.gz", ".tgz")):
            mode = "r:gz"
        else:
            mode = "r"
        
        with tarfile.open(archive, mode) as tar:
            _safe_extract(tar, tmp_path)
        
        _move_extracted_tree(tmp_path, destination, force=force)


def _safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    """Safely extract tarball, checking for path traversal."""
    destination = destination.resolve()
    for member in tar.getmembers():
        target = (destination / member.name).resolve()
        if destination != target and destination not in target.parents:
            raise DevlabError(f"Unsafe path in archive: {member.name}")
    try:
        tar.extractall(destination, filter="data")
    except TypeError:  # Python < 3.12
        tar.extractall(destination)


def _safe_extract_zip(zip_file: zipfile.ZipFile, destination: Path) -> None:
    """Safely extract ZIP, checking for path traversal."""
    destination = destination.resolve()
    for member in zip_file.infolist():
        target = (destination / member.filename).resolve()
        if destination != target and destination not in target.parents:
            raise DevlabError(f"Unsafe path in archive: {member.filename}")
    zip_file.extractall(destination)


def _mark_executables(path: Path) -> None:
    """Mark files as executable on Unix-like systems."""
    if not path.exists():
        return
    for file_path in path.iterdir():
        if not file_path.is_file():
            continue
        mode = file_path.stat().st_mode
        file_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
