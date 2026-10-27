"""Targeted Python-extension preloading."""

from __future__ import annotations

import sys

from mornye.extensions.manager import ExtensionManager


def _extension(root, name: str, source: str) -> None:
    directory = root / name
    directory.mkdir()
    (directory / "manifest.json").write_text(
        '{"name": "' + name + '", "runtime": "python", ' '"entryPoint": "entry.py"}',
        encoding="utf-8",
    )
    (directory / "entry.py").write_text(source, encoding="utf-8")


def test_selective_preload_leaves_unrelated_extensions_unimported(tmp_path) -> None:
    _extension(tmp_path, "needed-utility", "LOADED = True\n")
    _extension(
        tmp_path, "unrelated-provider", "raise RuntimeError('must not import')\n"
    )

    manager = ExtensionManager(ext_dir=tmp_path, auto_install_downloads=False)
    needed = "mornye.extensions_plugins.needed_utility"
    unrelated = "mornye.extensions_plugins.unrelated_provider"
    sys.modules.pop(needed, None)
    sys.modules.pop(unrelated, None)

    manager.preload_python_modules(only={"needed-utility"})

    assert sys.modules[needed].LOADED is True
    assert unrelated not in sys.modules
