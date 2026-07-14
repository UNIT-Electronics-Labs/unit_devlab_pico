from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from picodev.errors import PicodevError
from picodev.toolchain import ToolchainAsset, download_asset, find_cmake


class DownloadAssetTests(unittest.TestCase):
    @patch("picodev.toolchain.urllib.request.urlopen")
    @patch("picodev.toolchain.ssl.create_default_context")
    @patch("picodev.toolchain.certifi.where")
    def test_download_uses_certifi_ssl_context(
        self,
        certifi_where: MagicMock,
        create_default_context: MagicMock,
        urlopen: MagicMock,
    ) -> None:
        certifi_where.return_value = "ca-bundle.pem"
        ssl_context = create_default_context.return_value
        response = urlopen.return_value.__enter__.return_value
        response.headers = {"Content-Length": "8"}
        response.read.side_effect = [b"firmware", b""]
        asset = ToolchainAsset(
            platform="test",
            name="firmware.bin",
            url="https://example.com/firmware.bin",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / asset.name

            result = download_asset(asset, destination)

            self.assertEqual(result.read_bytes(), b"firmware")

        create_default_context.assert_called_once_with()
        ssl_context.load_verify_locations.assert_called_once_with(cafile="ca-bundle.pem")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, asset.url)
        self.assertEqual(request.get_header("User-agent"), "picodev toolchain installer")
        self.assertIs(urlopen.call_args.kwargs["context"], ssl_context)

    @patch("picodev.toolchain.urllib.request.urlopen")
    def test_failed_download_removes_partial_file(self, urlopen: MagicMock) -> None:
        response = urlopen.return_value.__enter__.return_value
        response.headers = {}
        response.read.side_effect = [b"partial", OSError("TLS failure")]
        asset = ToolchainAsset(
            platform="test",
            name="firmware.bin",
            url="https://example.com/firmware.bin",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / asset.name

            with self.assertRaisesRegex(PicodevError, "TLS failure"):
                download_asset(asset, destination)

            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".bin.part").exists())


class FindCMakeTests(unittest.TestCase):
    @patch("picodev.toolchain.sys.platform", "win32")
    @patch("picodev.toolchain.shutil.which", return_value=None)
    def test_finds_standard_windows_install_outside_current_path(self, _which) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "CMake" / "bin" / "cmake.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()

            with patch.dict(
                os.environ,
                {"ProgramFiles": temp_dir, "ProgramW6432": temp_dir},
                clear=True,
            ):
                result = find_cmake()

            self.assertEqual(result, str(executable))


class EnvironmentVariableTests(unittest.TestCase):
    """Test that toolchain path functions respect environment variables."""
    
    def test_gcc_install_path_respects_pico_toolchain_path_env(self) -> None:
        """Test that PICO_TOOLCHAIN_PATH environment variable is respected."""
        from picodev.toolchain import gcc_install_path
        
        custom_path = "/custom/path/to/toolchain"
        with patch.dict(os.environ, {"PICO_TOOLCHAIN_PATH": custom_path}):
            result = gcc_install_path()
            self.assertEqual(result, Path(custom_path))
    
    def test_gcc_install_path_expands_user_home(self) -> None:
        """Test that ~ is expanded in PICO_TOOLCHAIN_PATH."""
        from picodev.toolchain import gcc_install_path
        
        custom_path = "~/custom/toolchain"
        with patch.dict(os.environ, {"PICO_TOOLCHAIN_PATH": custom_path}):
            result = gcc_install_path()
            self.assertEqual(result, Path(custom_path).expanduser())
            self.assertNotIn("~", str(result))
    
    def test_pico_sdk_install_path_respects_pico_sdk_path_env(self) -> None:
        """Test that PICO_SDK_PATH environment variable is respected."""
        from picodev.toolchain import pico_sdk_install_path
        
        custom_path = "/custom/path/to/pico-sdk"
        with patch.dict(os.environ, {"PICO_SDK_PATH": custom_path}):
            result = pico_sdk_install_path()
            self.assertEqual(result, Path(custom_path))
    
    def test_pico_sdk_install_path_expands_user_home(self) -> None:
        """Test that ~ is expanded in PICO_SDK_PATH."""
        from picodev.toolchain import pico_sdk_install_path
        
        custom_path = "~/custom/pico-sdk"
        with patch.dict(os.environ, {"PICO_SDK_PATH": custom_path}):
            result = pico_sdk_install_path()
            self.assertEqual(result, Path(custom_path).expanduser())
            self.assertNotIn("~", str(result))
    
    def test_env_with_toolchain_uses_custom_paths(self) -> None:
        """Test that env_with_toolchain properly uses custom toolchain paths."""
        from picodev.toolchain import env_with_toolchain
        
        custom_gcc = "/custom/gcc/path"
        custom_sdk = "/custom/sdk/path"
        
        with patch.dict(os.environ, {
            "PICO_TOOLCHAIN_PATH": custom_gcc,
            "PICO_SDK_PATH": custom_sdk
        }, clear=False):
            env = env_with_toolchain()
            
            # Verify the environment variables are set correctly
            self.assertEqual(env["PICO_TOOLCHAIN_PATH"], custom_gcc)
            self.assertEqual(env["PICO_SDK_PATH"], custom_sdk)
            
            # Verify the bin directory is in PATH
            self.assertIn(f"{custom_gcc}{os.sep}bin", env["PATH"])


if __name__ == "__main__":
    unittest.main()
