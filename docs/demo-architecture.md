# Demo architecture

[Quick start](../README.md) | [Protocol architecture](protocol-architecture.md)

## Code responsibilities

| File | Responsibility |
| --- | --- |
| [`setup.py`](../setup.py) | Generate the demonstration CA, localhost certificate, and private keys |
| [`server.py`](../server.py) | Serve the same POST handler over loopback HTTP and TLS 1.3 |
| [`client.py`](../client.py) | Choose plaintext, trusted HTTPS, or untrusted HTTPS and submit the fake message |
| [`test_server.py`](../test_server.py) | Exercise request validation and idle connections using temporary certificates |

Paths for certificates and session logs are resolved relative to the scripts.
Use the [README setup commands](../README.md#prepare-powershell) to create `.venv`
and install `cryptography`, which the certificate generator and test setup require.

## Certificate and request flow

1. `setup.py` creates fresh CA and server key pairs and certificates in `certs/`.
   Rerunning it replaces the previous identities; restart the server afterward.
2. `server.py` loads the server certificate and key, configures TLS 1.3, and opens
   loopback listeners on ports 8000 and 8443.
3. `client.py` builds the same form body for each mode. HTTPS verifies the server
   before sending it; untrusted mode normally stops at certificate verification.
4. `DemoHandler` validates the request length, parses the form, and returns JSON.
   It derives `secure_transport` from the actual socket type.
5. Wireshark observes the loopback traffic. For trusted HTTPS, the client's key log
   can subsequently be supplied to decrypt that same captured connection.

## Connection handling and validation

`DemoServer` extends `ThreadingHTTPServer`. The HTTP accept loop runs in a
background thread and the HTTPS accept loop runs in the main thread. Both dispatch
connections to worker threads. HTTPS wrapping and handshaking occur in the worker,
so a peer that never sends a ClientHello cannot block the accept loop.

Each accepted socket has a five-second inactivity timeout. Idle connections are
closed; a body read that times out receives HTTP 408. This is not a total request
deadline: a peer that keeps sending data can extend the overall request duration.

`DemoHandler` accepts POST requests only at `/submit`. Its body reader applies
these checks before decoding the form:

| Condition | Response |
| --- | --- |
| Wrong POST path | 404 Not Found |
| Any `Transfer-Encoding` header | 400 Bad Request |
| Missing `Content-Length` | 411 Length Required |
| Duplicate, negative, or nondecimal length | 400 Bad Request |
| Body length above 4096 bytes | 413 Request Entity Too Large |
| Sender stops before the declared body arrives, leaving the connection open | 408 Request Timeout |
| Sender ends the stream before the declared body arrives | 400 Bad Request |

Zero-length bodies and bodies of exactly 4096 bytes are allowed. Error responses
close the connection so unread bytes cannot be interpreted as another request.
The handler implements the limited HTTP behavior needed by this local example.

## Regression checks

Run the [validation command](../README.md#validation-checks) from the project root.
The suite covers invalid framing, the body-size boundary, stalled and truncated
bodies, idle HTTP peers, and a verified HTTPS request alongside an idle TLS peer.
It generates temporary certificates and uses automatically assigned loopback ports.

## Capture walkthrough

First follow the README to start the server and capture loopback traffic with
`tcp.port == 8000 || tcp.port == 8443`. Run commands from the project directory;
leave Wireshark's TLS key-log preference empty for the encrypted view.

### Inspect the TLS version and handshake

Under filter `tcp.port == 8443`, select `Client Hello`, expand `Transport Layer Security > Handshake Protocol: Client Hello > Extension: supported_versions` and `Extension: key_share` (usually X25519 or another supported group). In `Server Hello`, expand supported_versions and the selected key share / Cipher Suite.

The TLS record version is a compatibility field, not the negotiated protocol
version. TLS 1.3 records use `0x0303`, with `0x0301` also permitted for the initial
ClientHello record. The selected version appears in the ServerHello
`supported_versions` extension and the client output. See the
[protocol explanation](protocol-architecture.md#what-the-capture-reveals).

Most of the handshake after ServerHello, including the server's Certificate, is encrypted. Wireshark cannot show them without session secrets. Thus `openssl s_client` or Python verified connection reports certificate data more readily than unconfigured Wireshark.

### Decrypt a captured session with its key log

1. The successful `.\.venv\Scripts\python.exe client.py https` created `tls-session-keys.log` in the kit directory.
2. In Wireshark navigate to **Edit > Preferences > Protocols > TLS**.
3. Set **(Pre)-Master-Secret log filename** to the **absolute path** of this file.
4. Click **OK**. Wireshark re-dissects the saved packets (or reload the capture if needed).
5. Filter `tcp.port == 8443` and examine `Decrypted TLS` / `HTTP` / **Follow > TLS Stream**. On a normal Wireshark build the original HTTP POST data should now become visible.
6. If HTTP doesn't automatically decode on the custom port, inspect the decrypted TLS pane and `Decode As` HTTP where appropriate; ensure TCP stream reassembly is enabled.

Wireshark uses the supplied session secrets to decode the existing capture.
The captured packets remain unchanged.

### Optional OpenSSL inspection

If OpenSSL CLI is installed:

```powershell
openssl s_client -connect localhost:8443 -servername localhost -tls1_3 -CAfile .\certs\demo-ca.pem -verify_hostname localhost -verify_return_error -brief
openssl x509 -in .\certs\demo-server.pem -noout -subject -issuer -dates -ext subjectAltName
```

Output from `s_client` can show `Protocol version: TLSv1.3`, cipher, and verified peer certificate. The local `CAfile` is trusted explicitly for this command only.
