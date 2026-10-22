# ACG CA1 — Topic 3: HTTPS/TLS 1.3 Demo Kit

This local example compares the same HTTP POST message over plaintext HTTP and
TLS 1.3 HTTPS. It also supports inspecting captured HTTPS traffic in Wireshark
using session secrets explicitly exported by the client.

## Documentation

- [Protocol architecture](docs/protocol-architecture.md): HTTP/1.1, TLS 1.3, certificate trust, and what a capture reveals.
- [Demo architecture](docs/demo-architecture.md): code responsibilities, connection handling, validation, and packet inspection steps.
- [Presenter guide](docs/presenter-guide.md): preparation, presentation schedule, and teaching notes.

## Requirements

- Python 3.10+ on Windows 10/11 (3.13 is fine)
- `cryptography`, installed in the project's `.venv` below (used ONLY for generating a test CA/server cert)
- Wireshark with **Npcap** (capture **Adapter for loopback traffic capture**)
- Optional OpenSSL command-line tool for certificate inspection

**Only uses localhost (127.0.0.1).** Neither real passwords nor real sites are required.

## Prepare (PowerShell)

```powershell
cd path\to\ACG_TLS13_Demo_Kit
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install cryptography
.\.venv\Scripts\python.exe setup.py
```

The `.venv` keeps the dependency separate from your global Python installation.
Run the commands below from the project directory in each terminal. They use the
virtual environment's Python directly, so activation is not required. Recreate
the `.venv` directory using these commands on each machine.

This creates a local demonstration CA and a leaf certificate for `localhost`, valid for 30 days. The leaf has a `subjectAltName` of `localhost`. Do **not** import the CA into your system-wide trusted roots. Keep the generated private-key files local.

## Start the server (PowerShell terminal 1)

```powershell
.\.venv\Scripts\python.exe server.py
```

Expected: `HTTP ready: http://localhost:8000/submit` and `HTTPS ready: https://localhost:8443/submit`.

## Start Wireshark capture

1. In Windows, select **Adapter for loopback traffic capture**. (Wi-Fi/Ethernet won't capture traffic to `localhost`.)
2. Start capture and apply a **display filter** (NOT a capture filter):
   `tcp.port == 8000 || tcp.port == 8443`
3. Leave **Edit > Preferences > Protocols > TLS > (Pre)-Master-Secret log filename** empty to inspect the capture without decryption.
4. Generate packets with terminal 2.

## Commands (PowerShell terminal 2)

```powershell
.\.venv\Scripts\python.exe client.py http
.\.venv\Scripts\python.exe client.py https
.\.venv\Scripts\python.exe client.py untrusted
```

- `http`: sends fake `ACG_SECRET_2026` in a POST body. In Wireshark filter `tcp.port == 8000`, find HTTP POST, **Follow > TCP Stream**. The fake message appears in plaintext.
- `https`: same POST over TLS 1.3 with verified server certificate trusted *only by this test client*. Capture on 8443 and see ClientHello / ServerHello and encrypted records. Printed TLS negotiated version/cipher may vary by OpenSSL builds.
- `untrusted`: uses only system trust roots, which do not trust the demo CA. Expected `SSLCertVerificationError`, illustrating that encrypted transport without authenticated server identity is not enough.

For handshake inspection and decryption using a session key log, continue with
the [capture walkthrough](docs/demo-architecture.md#capture-walkthrough).

## Validation checks

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_server
```

Tests generate temporary certificates and use automatically assigned loopback ports.
See [connection handling](docs/demo-architecture.md#connection-handling-and-validation)
for the server's limits and expected error responses.

## Troubleshooting

- **No packets:** wrong adapter; use Npcap loopback capture, not Wi-Fi or Ethernet.
- **Port already in use:** stop other services on 8000/8443 or change the ports in BOTH scripts.
- **Wireshark TLS shows 1.2:** distinguish legacy record version from `supported_versions`; also check `.\.venv\Scripts\python.exe client.py https` output.
- **No handshake:** start capture before running client. Each `.\.venv\Scripts\python.exe client.py https` starts a new process and fresh connection.
- **No secrets file:** make sure the command was `.\.venv\Scripts\python.exe client.py https` (not untrusted); check file in the demo kit directory.
- **TLS decryption fails:** check correct key log path and correct session, capture completeness, and `Edit > Preferences > Protocols > TCP` reassembly options.
- **Certificate expired or wrong hostname:** rerun `.\.venv\Scripts\python.exe setup.py` then restart server; do not trust demo CA globally.
- **OpenSSL command not found:** optional; the principal kit does not require OpenSSL CLI.

## Generated files

`setup.py` creates certificates and private keys in `certs/`. The HTTPS client
writes session secrets to `tls-session-keys.log`. Keep private keys and session
secrets local; they are excluded from Git by the project's `.gitignore`.
Regenerate certificates for each installation. `.venv/` is a local environment
and can be recreated from the setup instructions.
