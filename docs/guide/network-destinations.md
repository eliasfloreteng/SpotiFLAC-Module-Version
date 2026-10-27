# Network Destinations

Mornye supports host-mounted shares and saved SMB or WebDAV destinations:

1. Point the normal output directory at a share already mounted by the
   operating system. This uses the same filesystem path as a local folder.
2. Configure an SMB or WebDAV destination and let Mornye connect to the server
   directly.

Mornye does not mount shares, discover shares, or scan the local network.
Configure only SMB shares and WebDAV collections that you are authorized to use.

## Mounted shares

Mount the share with the operating system first, then choose that mount path
using the existing output-folder setting or CLI output argument:

- Windows: an absolute drive path or UNC path, such as `Z:\Music` or
  `\\nas.example.net\Music`.
- macOS: a mounted path such as `/Volumes/Music`.
- Linux: a mounted path such as `/mnt/music`.
- Docker: a path explicitly mounted into the container, such as
  `/mnt/network-music`.

Mornye does not attempt to mount or reconnect a disconnected operating-system
mount. The account running Mornye must have write access. In Docker, the path
must exist inside the container; a host mount is not automatically visible
there. See [Docker](docker.md#network-destinations-in-docker).

## Saved SMB destination profiles

SMB support is included in the standard Mornye installation; install it with
`python -m pip install mornye` (no `[smb]` extra is needed). In **Settings →
Download → Network Destinations**, choose **SMB**, then enter a profile name,
server hostname or IP, share name, and optional subfolder. Credentials use
the operating system's credential store when `keyring` selects a supported
secure backend (macOS Keychain, Windows Credential Manager, or Secret
Service). On unsupported/headless systems, credentials remain in memory for
the current process only and must be entered again after restart. Multi-user
web instances always keep credentials session-only
and scoped to the signed-in account. Passwords are never written to the
profile, general settings, job payload, or logs. Usernames are saved as
profile metadata. The profile file lives under Mornye's data directory and
is written with owner-only permissions where the platform supports them.

Use **Test Connection** before selecting the profile for new download jobs.
The test checks the share and destination directory, then creates and removes
a uniquely named temporary file to verify write permission. A failed test
reports a general connection or permission explanation and does not include
the password or raw SMB exception details.

When selected, Mornye runs the normal download, validation, metadata, tagging,
lyrics, and transcoding pipeline in a unique local staging directory. It then
uploads completed output using bounded chunks, checks size and SHA-256,
publishes by renaming a temporary remote file, and only then marks delivery
complete. Existing files are never overwritten: identical files are reused;
different-content name conflicts receive a numbered filename. If delivery
cannot complete, staged files are retained and the log includes a retry ID.
Select the destination again and use **Retry retained transfer** in settings.

The CLI can select a profile by name or ID. Create the profile in the GUI
first; the password is prompted through `getpass`, not accepted as a command
argument:

```bash
mornye 'https://open.spotify.com/track/…' --network-destination 'Home NAS'
```

The SMB backend uses the SMB2/SMB3 dialects supported by `smbprotocol`; it
does not fall back to SMB1. Enable **Require SMB3 encryption** only if the
server supports and requires it. Mornye does not disable server authentication
checks or reduce the negotiated security level to make a connection succeed.

For `--web` deployments, never send a password over plain HTTP. The web
interface rejects requests that include network destination passwords unless
the request scheme is HTTPS. Use TLS at the Mornye endpoint or a correctly configured
trusted reverse proxy. The desktop UI does not send credentials over the
network. Multi-user web instances allow only admins to create or remove shared
destination profiles; each logged-in account must test a profile with its own
session-only credentials before submitting downloads to it.

Transfers can be retried automatically after transient connection failures.
If a transfer still fails or is cancelled, the unique remote temporary file
is removed where possible and the local staged copy remains available for a
manual retry. Temporary files are never promoted to their final name until
verification succeeds.

## WebDAV destination profiles

WebDAV support is included in the standard installation and uses Mornye's
existing HTTP client. In **Settings → Download → Network Destinations**,
choose **WebDAV**, enter a profile name and collection URL, for example
`https://cloud.example.net/remote.php/dav/files/alice`, then optionally set a
subfolder, username, and password. Do not put credentials in the URL.
Passwords use the OS credential store when a supported secure backend is
available; otherwise they remain session-only. Multi-user web mode always
keeps passwords session-only.

Use **Test Connection** to check the collection and verify that Mornye can
write, read back, and remove a temporary file. WebDAV downloads are uploaded
to a temporary remote name, verified by size and SHA-256, then published with
the server's `MOVE` operation. Existing files are reused only when their
contents match; otherwise Mornye chooses a numbered filename. Interrupted
deliveries can be retried from the retained staging ID just like SMB
transfers.

The WebDAV server must support `PROPFIND`, `MKCOL`, `PUT`, `GET`, `HEAD`,
`MOVE`, and `DELETE` for the configured collection. Use HTTPS whenever
credentials or music traffic cross an untrusted network; Mornye does not
disable TLS certificate verification or follow redirects. Saved WebDAV
profiles can also be scanned read-only from the library statistics view.
In Docker, the container needs outbound network access to the WebDAV server.

## Docker network destinations

### WebDAV from the container

The published image includes WebDAV support. Create a WebDAV profile in the
settings UI; no extra image or port mapping is needed. The container needs
outbound HTTPS access to the configured collection. Use HTTPS rather than
sending credentials over an untrusted network.

### Host-mounted SMB share

Mount the SMB share on the Docker host first, then pass the mounted folder
through as a writable volume. This keeps SMB authentication and mounting
outside the container:

```yaml
services:
  mornye:
    environment:
      MORNYE_DOWNLOAD_DIR: /mnt/network-music
    volumes:
      - /mnt/nas/music:/mnt/network-music:rw
```

Replace the host path with the mount location on your machine. The host must
mount the share before Docker starts, and the container UID/GID must be allowed
to create directories and files there. On macOS, also allow the source path in
Docker Desktop's file-sharing settings. A host-mounted share is not implicitly
available inside the container.

### Native SMB from the container

The published Mornye image includes native SMB support. Use it with the
existing `--web` command and configure the SMB profile in the Mornye settings
UI:

The container needs outbound network access to the
configured server on TCP port 445 and a route/firewall rule that permits that
connection. Do not publish port 445 from the container, hardcode NAS
addresses, or put SMB credentials in Compose files or environment variables.
For remote browser access, use HTTPS; the container's default `--web` listener
is HTTP.

The same profile can be used with either deployment mode. A host-mounted share
uses the local filesystem path; native SMB connects directly to the configured
server.
