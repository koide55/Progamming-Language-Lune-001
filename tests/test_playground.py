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

    def test_playground_uses_relative_paths(self) -> None:
        """GitHub Pages serves the site under a subpath — absolute /lune/ breaks."""
        html = (ROOT / "playground" / "index.html").read_text(encoding="utf-8")
        self.assertIn("fetch(`../lune/${f}`", html)
        self.assertNotIn("fetch(`/lune/", html)

    def test_error_catalog_page_references_both_indexes(self) -> None:
        html = (ROOT / "playground" / "errors.html").read_text(encoding="utf-8")
        self.assertIn("../documents/ERROR_INDEX_JA.md", html)
        self.assertIn("../documents/ERROR_INDEX.md", html)

    def test_landing_page_links_playground_and_catalog(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="playground/"', html)
        self.assertIn('href="playground/errors.html"', html)


if __name__ == "__main__":
    unittest.main()
