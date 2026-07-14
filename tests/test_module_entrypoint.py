from __future__ import annotations

import subprocess
import sys
import unittest


class ModuleEntrypointTests(unittest.TestCase):
    def test_python_m_picodev_reports_version(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "picodev", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "picodev 0.1.12")


if __name__ == "__main__":
    unittest.main()
