"""Load optional metadata/session utilities from the installed extension.

The implementation is deliberately not bundled with Mornye.  Install the
``utilities.sflx`` package through a configured registry or a links file, and
this gateway exposes its modules under the legacy ``mornye.core.*`` names.
"""

from __future__ import annotations

import importlib
import threading
from types import ModuleType

from .manager import ExtensionManager

EXTENSION_ID = "utilities"
MODULES = frozenset(
    {
        "spotify_metadata",
        "spotify_protobuf",
        "spotify_totp",
        "spotfetch",
        "tidal_metadata",
        "solver",
        "signed_session_errors",
        "signed_session_mobile",
        "signed_session_desktop",
        "signed_session_mono",
        "signed_session_status",
    }
)

_load_lock = threading.RLock()


def _manager_with_utilities() -> ExtensionManager:
    """Return a manager after attempting the normal registry/link install."""
    # Avoid a registry request for every metadata lookup: a normal installed
    # utilities package needs no network before it can be used.
    manager = ExtensionManager(auto_install_downloads=False)
    if manager.get_installed(EXTENSION_ID) is not None:
        return manager

    # The package is missing, so use the normal registry bootstrap first.
    # This preserves automatic updates and registry trust verification.
    manager = ExtensionManager(auto_install_downloads=True)
    if manager.get_installed(EXTENSION_ID) is None:
        # Supports MORNYE_EXT_LINKS or ~/.mornye/extensions/extensions_links.env
        # in addition to normal MORNYE_REGISTRIES bootstrap.
        try:
            manager.install_from_links_file()
        except FileNotFoundError:
            pass
    return manager


def load_module(name: str) -> ModuleType:
    """Load one module supplied by the externally installed utilities package."""
    if name not in MODULES:
        raise ValueError(f"Unknown utilities module: {name}")

    with _load_lock:
        manager = _manager_with_utilities()
        if manager.get_installed(EXTENSION_ID) is None:
            raise RuntimeError(
                "The utilities extension is not installed. Configure "
                "MORNYE_REGISTRIES with a registry containing utilities.sflx, "
                "or provide its URL through MORNYE_EXT_LINKS."
            )
        # A request for ``signed_session_status`` is deliberately local: do
        # not preload every Python provider just to inspect session files.
        # Some providers initialise signed-session/browser machinery during
        # import, which used to leave the TUI on a blank screen at startup.
        manager.preload_python_modules(only={EXTENSION_ID})
        return importlib.import_module(f"mornye.extensions_plugins.{name}")
