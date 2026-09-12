"""Tests for python/print_books.py find_binary(). Stdlib unittest only."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python import print_books


def _touch_exe(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/true\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class FindBinaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)

    def _patch_roots(self) -> None:
        """Point the launcher at an empty fake repo; clear env discovery."""
        script = self.root / "python" / "print_books.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("# fake launcher for samefile checks\n", encoding="utf-8")
        self.fake_script = script.resolve()
        self.patches = [
            mock.patch.object(print_books, "_SCRIPT", self.fake_script),
            mock.patch.object(print_books, "_REPO_ROOT", self.root),
            mock.patch.dict(os.environ, {"PATH": "", "PRINT_BOOKS_BIN": ""}, clear=False),
        ]
        # Remove PRINT_BOOKS_BIN entirely when empty string would still be "set".
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("PRINT_BOOKS_BIN", None)
        os.environ["PATH"] = ""

    def test_env_wins(self) -> None:
        self._patch_roots()
        env_bin = _touch_exe(self.root / "from_env" / "print-books")
        path_bin = _touch_exe(self.root / "on_path" / "print-books")
        well = _touch_exe(self.root / "build" / "linux" / "cli" / "print-books")
        os.environ["PRINT_BOOKS_BIN"] = str(env_bin)
        os.environ["PATH"] = str(path_bin.parent)
        self.assertEqual(print_books.find_binary(), str(env_bin.resolve()))
        self.assertTrue(well.exists())  # present but lower priority

    def test_path_wins_over_well_known(self) -> None:
        self._patch_roots()
        path_bin = _touch_exe(self.root / "on_path" / "print-books")
        _touch_exe(self.root / "build" / "linux" / "cli" / "print-books")
        os.environ["PATH"] = str(path_bin.parent)
        self.assertEqual(print_books.find_binary(), str(path_bin.resolve()))

    def test_path_skips_this_script(self) -> None:
        self._patch_roots()
        # Put a copy of "this script" on PATH under the name print-books.
        decoy = self.root / "on_path" / "print-books"
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text("# fake launcher for samefile checks\n", encoding="utf-8")
        decoy.chmod(decoy.stat().st_mode | stat.S_IXUSR)
        # samefile with _SCRIPT: replace _SCRIPT to match the decoy inode.
        with mock.patch.object(print_books, "_SCRIPT", decoy.resolve()):
            well = _touch_exe(self.root / "build" / "linux_debug" / "cli" / "print-books")
            os.environ["PATH"] = str(decoy.parent)
            self.assertEqual(print_books.find_binary(), str(well.resolve()))

    def test_well_known_linux_then_debug(self) -> None:
        self._patch_roots()
        debug = _touch_exe(self.root / "build" / "linux_debug" / "cli" / "print-books")
        self.assertEqual(print_books.find_binary(), str(debug.resolve()))
        release = _touch_exe(self.root / "build" / "linux" / "cli" / "print-books")
        self.assertEqual(print_books.find_binary(), str(release.resolve()))

    def test_well_known_native_and_custom(self) -> None:
        self._patch_roots()
        custom = _touch_exe(
            self.root / "build" / "linux_custom-v3" / "cli" / "print-books"
        )
        self.assertEqual(print_books.find_binary(), str(custom.resolve()))
        native = _touch_exe(
            self.root / "build" / "linux_native" / "cli" / "print-books"
        )
        # Named native entries are checked before the custom-* glob.
        self.assertEqual(print_books.find_binary(), str(native.resolve()))

    def test_missing_returns_none(self) -> None:
        self._patch_roots()
        self.assertIsNone(print_books.find_binary())

    def test_main_exits_127_when_missing(self) -> None:
        self._patch_roots()
        with self.assertRaises(SystemExit) as ctx:
            print_books.main()
        self.assertEqual(ctx.exception.code, 127)

    def test_env_skips_this_script(self) -> None:
        self._patch_roots()
        with mock.patch.object(print_books, "_SCRIPT", self.fake_script):
            os.environ["PRINT_BOOKS_BIN"] = str(self.fake_script)
            # Make the fake script "executable" so the env branch considers it.
            self.fake_script.chmod(self.fake_script.stat().st_mode | stat.S_IXUSR)
            well = _touch_exe(self.root / "build" / "linux" / "cli" / "print-books")
            self.assertEqual(print_books.find_binary(), str(well.resolve()))


if __name__ == "__main__":
    unittest.main()
