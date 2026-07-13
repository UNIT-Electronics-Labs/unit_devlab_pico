from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from devlab.errors import DevlabError
from devlab.project import clean_project, create_project, flash_project, load_config


class CreateProjectTests(unittest.TestCase):
    def test_creates_flat_project_with_recommended_cmake_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "00_Blink_Practice"

            create_project("00_Blink_Practice", directory=root)

            self.assertTrue((root / "main.c").is_file())
            self.assertTrue((root / "pico_sdk_import.cmake").is_file())
            self.assertFalse((root / "src").exists())

            cmake = (root / "CMakeLists.txt").read_text()
            self.assertIn("cmake_minimum_required(VERSION 3.20)", cmake)
            self.assertIn("include(pico_sdk_import.cmake)", cmake)
            self.assertIn('set(PROJECT_NAME    "00_Blink_Practice")', cmake)
            self.assertIn('set(PROJECT_SOURCES "main.c")', cmake)
            self.assertIn('set(PICO_BOARD      "pico")', cmake)
            self.assertIn("hardware_gpio", cmake)
            self.assertIn("pico_enable_stdio_usb(${PROJECT_NAME} 1)", cmake)
            self.assertIn("pico_enable_stdio_uart(${PROJECT_NAME} 0)", cmake)

            config = load_config(root / "picodev.toml")
            self.assertEqual(config.sources, ["main.c"])

    def test_pico_w_links_cyw43_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wifi-blink"

            create_project("wifi-blink", directory=root, board="pico_w")

            cmake = (root / "CMakeLists.txt").read_text()
            self.assertIn('set(PICO_BOARD      "pico_w")', cmake)
            self.assertIn("pico_cyw43_arch_none", cmake)

    def test_pico2_is_written_to_cmake_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pico2-blink"

            create_project("pico2-blink", directory=root, board="pico2")

            cmake = (root / "CMakeLists.txt").read_text()
            self.assertIn('set(PICO_BOARD      "pico2")', cmake)

    def test_unit_boards_map_to_their_rp_sdk_boards(self) -> None:
        cases = (
            ("pulsar_rp", "pico2", "rp2350"),
            ("dualmcu_rp", "pico", "rp2040"),
        )

        for board, sdk_board, pyocd_target in cases:
            with self.subTest(board=board), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / board
                create_project(board, directory=root, board=board)

                config_path = root / "picodev.toml"
                config = load_config(config_path)
                cmake = (root / "CMakeLists.txt").read_text()

                self.assertEqual(config.board, board)
                self.assertIn(f'set(PICO_BOARD      "{sdk_board}")', cmake)

                output = StringIO()
                with redirect_stdout(output):
                    flash_project(config_path=config_path, dry_run=True)
                self.assertIn(f"--target {pyocd_target}", output.getvalue())


class CleanProjectTests(unittest.TestCase):
    def test_removes_configured_build_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "blink"
            create_project("blink", directory=root)
            build_dir = root / "build"
            build_dir.mkdir()
            (build_dir / "blink.uf2").write_text("firmware")

            cleaned_path, removed = clean_project(root / "picodev.toml")

            self.assertEqual(cleaned_path, build_dir)
            self.assertTrue(removed)
            self.assertFalse(build_dir.exists())

    def test_is_idempotent_when_build_directory_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "blink"
            create_project("blink", directory=root)

            cleaned_path, removed = clean_project(root / "picodev.toml")

            self.assertEqual(cleaned_path, root / "build")
            self.assertFalse(removed)

    def test_refuses_to_remove_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "blink"
            create_project("blink", directory=root)
            config_path = root / "picodev.toml"
            config_path.write_text(
                '[pico]\nboard = "pico"\n\n[build]\n'
                'name = "blink"\nbuild_dir = "."\nsources = ["main.c"]\n'
            )

            with self.assertRaisesRegex(DevlabError, "project root"):
                clean_project(config_path)


if __name__ == "__main__":
    unittest.main()
