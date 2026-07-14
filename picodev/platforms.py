from __future__ import annotations

import platform
from dataclasses import dataclass

from .errors import PicodevError


@dataclass(frozen=True)
class PlatformId:
    os_name: str
    arch: str

    @property
    def key(self) -> str:
        return f"{self.os_name}-{self.arch}"


def current_platform() -> PlatformId:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        os_name = "linux"
    elif system == "darwin":
        os_name = "darwin"
    elif system in {"windows", "msys", "cygwin"}:
        os_name = "windows"
    else:
        raise PicodevError(f"Unsupported operating system: {platform.system()}")

    if machine in {"x86_64", "amd64"}:
        arch = "x64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise PicodevError(f"Unsupported CPU architecture: {platform.machine()}")

    return PlatformId(os_name=os_name, arch=arch)
