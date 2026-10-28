from __future__ import annotations

import subprocess
import sys


def test_core_package_does_not_expose_legacy_utility_modules_eagerly() -> None:
    code = "import mornye.core; print('spotify_metadata' in dir(mornye.core)); print('signed_session_mobile' in dir(mornye.core))"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines == ["False", "False"]


def test_legacy_utility_aliases_still_import_when_explicitly_requested() -> None:
    code = (
        "import importlib; "
        "mod = importlib.import_module('mornye.core.spotify_metadata'); "
        "print(mod.__name__); "
        "print(mod is importlib.import_module('mornye.core.spotify_metadata'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines == ["mornye.core.spotify_metadata", "True"]
