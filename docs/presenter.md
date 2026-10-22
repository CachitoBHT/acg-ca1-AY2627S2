# Presenter guide

[Quick start](../README.md) | [Protocol architecture](protocol-architecture.md) | [Demo architecture](demo-architecture.md)

Presenter stuff incase forget.
Installation and usage instructions are in the README; packet inspection steps
are in the [capture walkthrough](demo-architecture.md#capture-walkthrough).

## Preparation

- Generate certificates and check all three client modes before presenting.
- Start a loopback capture before running the clients so the handshake is recorded.
- Clear Wireshark's TLS key-log preference before showing the encrypted capture.
- Keep the capture and its matching `tls-session-keys.log` available for the reveal.
- Use the fake message supplied with the project throughout the presentation.

## Recommended presentation order (5–6 mins)

- 0:00–0:40 Introduce three roles and the fake message.
- 0:40–1:25 HTTP plaintext capture, point at body in Follow TCP Stream.
- 1:25–2:45 HTTPS session, TLS 1.3 supported_versions/key_share/cipher suite.
- 2:45–3:25 Discuss encrypted application data and certificate identity.
- 3:25–4:30 Add only your local TLS session key log and reveal the same HTTP body.
- 4:30–5:10 Optional untrusted certificate verification failure.
- 5:10–5:40 Summarize exactly what the experiment proves and does not prove.

## Teaching notes

- Compare the same form body over HTTP and HTTPS to isolate the transport difference.
- Distinguish HTTP/1.1 (application protocol) from TLS 1.3 (connection protection).
- Point to `supported_versions` or the client's negotiated-version output when
  identifying TLS 1.3; the legacy record-version field is a compatibility value.
- Explain that adding the key log changes what Wireshark can decode from the same
  capture. It supplies session secrets rather than breaking TLS encryption.
- Use the untrusted mode to explain certificate authentication and scoped trust.
- Close by describing what the experiment establishes and its limits: local test
  traffic, explicit trust configuration, and deliberately exported secrets.

## Sharing presentation materials

Share source files and documentation, with a sanitized recording or packet trace
if needed. Exclude `.venv/`, private-key files, session key logs, and any real
traffic secrets. Other users can regenerate their own local certificates.
