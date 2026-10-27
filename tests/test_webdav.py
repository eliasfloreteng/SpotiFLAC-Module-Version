from __future__ import annotations

import httpx
import pytest

from mornye.core.network_destinations import (
    DestinationError,
    DestinationStore,
    WebDAVProfile,
    create_backend,
    validate_profile,
)
from mornye.core.webdav import WebDAVBackend


def _profile(**changes):
    values = {
        "type": "webdav",
        "id": "webdav1234",
        "name": "Cloud Music",
        "url": "https://cloud.example.net/dav/alice",
        "username": "alice",
        "subdirectory": "Music",
    }
    values.update(changes)
    return validate_profile(values)


class _FakeWebDAV:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.collections = {self.base}
        self.files: dict[str, bytes] = {}
        self.requests: list[tuple[str, str, dict, bytes]] = []

    def request(self, method, url, *, headers=None, content=None):
        body = content.read() if hasattr(content, "read") else (content or b"")
        request_headers = headers or {}
        self.requests.append((method, url, request_headers, body))
        if method == "PROPFIND":
            if url not in self.collections:
                return httpx.Response(404)
            children = []
            for path in self.collections:
                if path != url and path.rsplit("/", 1)[0] == url:
                    children.append(
                        f"<d:response><d:href>{path}</d:href>"
                        "<d:propstat><d:prop><d:resourcetype>"
                        "<d:collection/></d:resourcetype></d:prop>"
                        "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                    )
            for path, data in self.files.items():
                if path.rsplit("/", 1)[0] == url:
                    children.append(
                        f"<d:response><d:href>{path}</d:href>"
                        "<d:propstat><d:prop><d:resourcetype/>"
                        f"<d:getcontentlength>{len(data)}</d:getcontentlength>"
                        "</d:prop><d:status>HTTP/1.1 200 OK</d:status>"
                        "</d:propstat></d:response>"
                    )
            xml = (
                "<d:multistatus xmlns:d='DAV:'>"
                f"<d:response><d:href>{url}/</d:href>"
                "<d:propstat><d:prop><d:resourcetype><d:collection/>"
                "</d:resourcetype></d:prop>"
                "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                + "".join(children)
                + "</d:multistatus>"
            )
            return httpx.Response(207, content=xml)
        if method == "MKCOL":
            self.collections.add(url)
            return httpx.Response(201)
        if method == "PUT":
            self.files[url] = body
            return httpx.Response(201)
        if method == "HEAD":
            if url not in self.files:
                return httpx.Response(404)
            return httpx.Response(
                200, headers={"content-length": str(len(self.files[url]))}
            )
        if method == "GET":
            return httpx.Response(200, content=self.files[url])
        if method == "MOVE":
            self.files[request_headers["Destination"]] = self.files.pop(url)
            return httpx.Response(201)
        if method == "DELETE":
            self.files.pop(url, None)
            return httpx.Response(204)
        raise AssertionError(method)


def test_webdav_profile_validation_rejects_unsafe_urls_and_paths():
    for url in (
        "ftp://cloud.example.net/dav",
        "https://alice:secret@cloud.example.net/dav",
        "https://cloud.example.net/dav?token=secret",
        "https://cloud.example.net/dav/%2e%2e/private",
    ):
        with pytest.raises(DestinationError):
            _profile(url=url)
    with pytest.raises(DestinationError, match="subfolder"):
        _profile(subdirectory="../private")


def test_webdav_profiles_round_trip_and_keep_existing_smb_profiles(tmp_path):
    store = DestinationStore(tmp_path / "destinations.json")
    saved = store.save(_profile().public_dict(), "secret")

    assert isinstance(saved, WebDAVProfile)
    assert store.get(saved.id) == saved
    assert store.credentials(saved) == "secret"
    assert store.list()[0]["type"] == "webdav"

    smb = validate_profile(
        {
            "id": "smbprofile123",
            "name": "NAS",
            "host": "nas.example.net",
            "share": "Music",
        }
    )
    store.save(smb.public_dict())
    assert [profile["type"] for profile in store.list()] == ["webdav", "smb"]


def test_webdav_connection_test_creates_and_removes_probe():
    profile = _profile()
    fake = _FakeWebDAV(profile.url)
    backend = WebDAVBackend(profile, profile.username, "secret", client=fake)

    result = backend.test_connection()

    assert result["ok"] is True
    assert fake.files == {}
    assert [method for method, *_ in fake.requests] == [
        "PROPFIND",
        "PROPFIND",
        "MKCOL",
        "PUT",
        "GET",
        "DELETE",
    ]


def test_webdav_upload_verifies_before_publishing_and_preserves_conflicts(tmp_path):
    profile = _profile(subdirectory="")
    fake = _FakeWebDAV(profile.url)
    fake.files[f"{profile.url}/track.flac"] = b"existing different content"
    backend = create_backend(profile, profile.username, "secret")
    backend._client = fake
    staged = tmp_path / "track.flac"
    staged.write_bytes(b"new lossless audio")

    remote_paths = backend.upload_tree(tmp_path)

    assert remote_paths == [f"{profile.url}/track%20%281%29.flac"]
    assert fake.files[f"{profile.url}/track.flac"] == b"existing different content"
    assert fake.files[remote_paths[0]] == staged.read_bytes()
    methods = [method for method, *_ in fake.requests]
    assert methods.index("PUT") < methods.index("GET") < methods.index("MOVE")


def test_webdav_library_listing_and_audio_reads_are_read_only():
    profile = _profile(subdirectory="")
    fake = _FakeWebDAV(profile.url)
    track = f"{profile.url}/track.flac"
    fake.files[track] = b"audio"
    backend = WebDAVBackend(profile, profile.username, "secret", client=fake)

    files = backend.list_audio_files()
    with backend.open_audio_file(files[0]["path"]) as audio:
        content = audio.read()

    assert files == [{"path": track, "size": 5, "modified": None}]
    assert content == b"audio"
    assert all(method in {"PROPFIND", "GET"} for method, *_ in fake.requests)


def test_webdav_library_scan_marks_report_source_and_decodes_remote_names(
    monkeypatch,
):
    from mornye.core import smb_library_scan as scan

    profile = _profile(subdirectory="")

    class Backend:
        def list_audio_files(self):
            return [{"path": f"{profile.url}/a%20track.flac", "size": 20}]

    monkeypatch.setattr(scan, "create_backend", lambda *_args: Backend())
    monkeypatch.setattr(
        scan,
        "_read_remote_file",
        lambda _backend, _item: {
            "title": "Track",
            "artist": "Artist",
            "album": "Album",
            "genre": "",
            "release_year": "",
            "duration_ms": 1000,
            "format": "flac",
            "bytes": 20,
        },
    )

    report = scan.scan_smb_library(profile, profile.username, "secret")

    assert report["source"] == "webdav"
    assert report["window"]["label"] == "WEBDAV library"
