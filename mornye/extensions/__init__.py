"""Mornye's installed and built-in extension system.

Exports are loaded lazily: core code may use a built-in extension without
initialising Node runtimes or the extension registry.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "REGISTRY_URL",
    # Manager
    "ExtensionManager",
    "ExtensionRuntimeError",
    "InstalledExtension",
    # Provider
    "JSExtensionProvider",
    "PythonExtensionProvider",
    # Runtime
    "JSRuntime",
    "RegistryEntry",
    "SERVICE_ALIASES",
    "extension_id",
    "make_extension_provider",
]

_EXPORTS = {
    "REGISTRY_URL": (".manager", "REGISTRY_URL"),
    "ExtensionManager": (".manager", "ExtensionManager"),
    "InstalledExtension": (".manager", "InstalledExtension"),
    "RegistryEntry": (".manager", "RegistryEntry"),
    "ExtensionRuntimeError": (".runtime", "ExtensionRuntimeError"),
    "JSRuntime": (".runtime", "JSRuntime"),
    "JSExtensionProvider": (".provider", "JSExtensionProvider"),
    "PythonExtensionProvider": (".python_provider", "PythonExtensionProvider"),
    "make_extension_provider": (".provider", "make_extension_provider"),
    "SERVICE_ALIASES": (".catalog", "SERVICE_ALIASES"),
    "extension_id": (".catalog", "extension_id"),
}


def __getattr__(name: str) -> Any:
    """Load public extension APIs only when a caller asks for them."""
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
