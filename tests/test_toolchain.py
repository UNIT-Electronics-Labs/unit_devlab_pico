from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from picodev.errors import PicodevError
from picodev.toolchain import ToolchainAsset, download_asset


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


if __name__ == "__main__":
    unittest.main()
