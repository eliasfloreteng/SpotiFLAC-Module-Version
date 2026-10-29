from __future__ import annotations

from mornye import downloader
from mornye.application import download_engine


def test_compat_module_deletes_forwarded_attributes_on_restore(monkeypatch) -> None:
    name = "_compat_test_missing_attribute"
    value = object()
    assert not hasattr(download_engine, name)

    with monkeypatch.context() as patch:
        patch.setattr(downloader, name, value, raising=False)
        assert getattr(download_engine, name) is value

    assert not hasattr(download_engine, name)


def test_compat_module_restores_forwarded_attributes_on_restore(monkeypatch) -> None:
    original = download_engine.DownloadManager
    replacement = object()

    with monkeypatch.context() as patch:
        patch.setattr(downloader, "DownloadManager", replacement)
        assert download_engine.DownloadManager is replacement

    assert download_engine.DownloadManager is original
