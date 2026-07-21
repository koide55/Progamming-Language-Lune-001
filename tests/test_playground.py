from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PlaygroundTests(unittest.TestCase):
    def test_playground_fetches_every_lune_module(self) -> None:
        """playground/index.html hardcodes the module list; it must not go stale.

        (A missing entry surfaces only at runtime in the browser as a
        ModuleNotFoundError — this has happened twice.)
        """
        html = (ROOT / "playground" / "index.html").read_text(encoding="utf-8")
        match = re.search(r"const LUNE_FILES = \[(.*?)\];", html, re.DOTALL)
        assert match is not None, "LUNE_FILES not found in playground/index.html"
        listed = set(re.findall(r'"([\w.]+\.py)"', match.group(1)))
        actual = {path.name for path in (ROOT / "lune").glob("*.py")}
        self.assertEqual(listed, actual)


if __name__ == "__main__":
    unittest.main()
