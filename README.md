# ACG CA1 — Topic 3: HTTPS/TLS 1.3 Demo Kit

**Goal:** use the same fake HTTP POST message to show plaintext on HTTP, protected TLS 1.3 on HTTPS, and decryption of your *own* captured session when its traffic secrets are explicitly supplied to Wireshark.

## Requirements

- Python 3.10+ on Windows 10/11 (3.13 is fine)
- `python -m pip install cryptography` (used ONLY for generating a test CA/server cert)
- Wireshark with **Npcap** (capture **Adapter for loopback traffic capture**)
- Optional OpenSSL command-line tool for certificate inspection

**Only uses localhost (127.0.0.1).** Neither real passwords nor real sites are required.

## Prepare (PowerShell)

```powershell
cd path\to\ACG_TLS13_Demo_Kit
python -m pip install cryptography
python setup.py
```

This creates a local demonstration CA and a leaf certificate for `localhost`, valid for 30 days. The leaf has a `subjectAltName` of `localhost`. Do **not** import the CA into your system-wide trusted roots. Do **not** submit private-key files.

## Start the server (PowerShell terminal 1)

```powershell
python server.py
```

Expected: `HTTP ready: http://localhost:8000/submit` and `HTTPS ready: https://localhost:8443/submit`.

## Start Wireshark capture

1. In Windows, select **Adapter for loopback traffic capture**. (Wi-Fi/Ethernet won't capture traffic to `localhost`.)
2. Start capture and apply a **display filter** (NOT a capture filter):
   `tcp.port == 8000 || tcp.port == 8443`
3. Leave **Edit > Preferences > Protocols > TLS > (Pre)-Master-Secret log filename** empty until after demonstrating encrypted traffic.
4. Generate packets with terminal 2.

## Commands (PowerShell terminal 2)

```powershell
python client.py http
python client.py https
python client.py untrusted
```

- `http`: sends fake `ACG_SECRET_2026` in a POST body. In Wireshark filter `tcp.port == 8000`, find HTTP POST, **Follow > TCP Stream**. The fake message appears in plaintext.
- `https`: same POST over TLS 1.3 with verified server certificate trusted *only by this test client*. Capture on 8443 and see ClientHello / ServerHello and encrypted records. Printed TLS negotiated version/cipher may vary by OpenSSL builds.
- `untrusted`: uses only system trust roots, which do not trust the demo CA. Expected `SSLCertVerificationError`, illustrating that encrypted transport without authenticated server identity is not enough.

## Show TLS version and handshake

Under filter `tcp.port == 8443`, select `Client Hello`, expand `Transport Layer Security > Handshake Protocol: Client Hello > Extension: supported_versions` and `Extension: key_share` (usually X25519 or another supported group). In `Server Hello`, expand supported_versions and the selected key share / Cipher Suite.

**Important:** TLS 1.3 keeps the legacy record version `0x0303` for compatibility; don't present that field as negotiated TLS 1.2. Use the `supported_versions` extension or client output.

Most of the handshake after ServerHello, including the server's Certificate, is encrypted. Wireshark cannot show them without session secrets. Thus `openssl s_client` or Python verified connection reports certificate data more readily than unconfigured Wireshark.

## Reveal the *same* TLS session by adding the key log AFTER capture

1. The successful `python client.py https` created `tls-session-keys.log` in the kit directory.
2. In Wireshark navigate to **Edit > Preferences > Protocols > TLS**.
3. Set **(Pre)-Master-Secret log filename** to the **absolute path** of this file.
4. Click **OK**. Wireshark re-dissects the saved packets (or reload the capture if needed).
5. Filter `tcp.port == 8443` and examine `Decrypted TLS` / `HTTP` / **Follow > TLS Stream**. On a normal Wireshark build the original HTTP POST data should now become visible.
6. If HTTP doesn't automatically decode on the custom port, inspect the decrypted TLS pane and `Decode As` HTTP where appropriate; ensure TCP stream reassembly is enabled.

**Point to teach:** the capture was the same throughout. Wireshark acquired extra authorized cryptographic material, not the ability to break TLS.

## Optional OpenSSL investigation

If OpenSSL CLI is installed:

```powershell
openssl s_client -connect localhost:8443 -servername localhost -tls1_3 -CAfile .\certs\demo-ca.pem -verify_hostname localhost -verify_return_error -brief
openssl x509 -in .\certs\demo-server.pem -noout -subject -issuer -dates -ext subjectAltName
```

Output from `s_client` can show `Protocol version: TLSv1.3`, cipher, and verified peer certificate. The local `CAfile` is trusted explicitly for this command only.

## Recommended presentation order (5–6 mins)

- 0:00–0:40 Introduce three roles and the fake message.
- 0:40–1:25 HTTP plaintext capture, point at body in Follow TCP Stream.
- 1:25–2:45 HTTPS session, TLS 1.3 supported_versions/key_share/cipher suite.
- 2:45–3:25 Discuss encrypted application data and certificate identity.
- 3:25–4:30 Add only your local TLS session key log and reveal the same HTTP body.
- 4:30–5:10 Optional untrusted certificate verification failure.
- 5:10–5:40 Summarize exactly what the experiment proves and does not prove.

## Troubleshooting

The server closes idle connections after 5 seconds. TLS handshakes run in separate
workers so an idle TLS peer does not block other clients. POST requests require a
single nonnegative decimal `Content-Length` of at most 4096 bytes; transfer
encoding is unsupported. Invalid framing closes the connection, and stalled
request bodies receive HTTP 408. These are inactivity timeouts, not a total
request deadline.

Run the local validation and idle-connection checks with
`python -m unittest -v test_server`. Tests generate temporary certificates and
use automatically assigned loopback ports.

- **No packets:** wrong adapter; use Npcap loopback capture, not Wi-Fi or Ethernet.
- **Port already in use:** stop other services on 8000/8443 or change the ports in BOTH scripts.
- **Wireshark TLS shows 1.2:** distinguish legacy record version from `supported_versions`; also check `python client.py https` output.
- **No handshake:** start capture before running client. Each `python client.py https` starts a new process and fresh connection.
- **No secrets file:** make sure the command was `python client.py https` (not untrusted); check file in the demo kit directory.
- **TLS decryption fails:** check correct key log path and correct session, capture completeness, and `Edit > Preferences > Protocols > TCP` reassembly options.
- **Certificate expired or wrong hostname:** rerun `python setup.py` then restart server; do not trust demo CA globally.
- **OpenSSL command not found:** optional; the principal kit does not require OpenSSL CLI.

## Files to submit / not submit

Share source files: `setup.py`, `server.py`, `client.py`, this README; optionally a short *sanitized* recording/packet trace. **Do not submit** `certs/*-key.pem`, `tls-session-keys.log`, or any real traffic secrets. Regenerate lab certificates independently.

## Standards / official documentation

- IETF RFC 8446, TLS 1.3: https://www.rfc-editor.org/rfc/rfc8446.html
- Wireshark TLS wiki: https://wiki.wireshark.org/TLS/
- Wireshark loopback capture: https://wiki.wireshark.org/captureSetup/loopback
- Python ssl: https://docs.python.org/3/library/ssl.html
- Python http.server: https://docs.python.org/3/library/http.server.html
