"""Run matching HTTP (8000) and TLS 1.3 HTTPS (8443) local-only demo services."""
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent
CONNECTION_TIMEOUT = 5
MAX_BODY_BYTES = 4096


class DemoServer(ThreadingHTTPServer):
    """Bound idle waits and perform TLS handshakes inside request workers."""

    def __init__(self, address, handler, *, tls_context=None,
                 connection_timeout=CONNECTION_TIMEOUT):
        self.tls_context = tls_context
        self.connection_timeout = connection_timeout
        super().__init__(address, handler)

    def process_request_thread(self, request, client_address):
        try:
            request.settimeout(self.connection_timeout)
            if self.tls_context is not None:
                request = self.tls_context.wrap_socket(
                    request, server_side=True, do_handshake_on_connect=False)
                request.do_handshake()
        except OSError:
            # Idle or invalid TLS peers must not stop the accept loop.
            self.shutdown_request(request)
            return
        super().process_request_thread(request, client_address)


class DemoHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def read_body(self):
        """Return a bounded body, or send an error and close the connection."""
        if self.headers.get_all('Transfer-Encoding') is not None:
            self.send_error(400, 'Transfer-Encoding is not supported')
            return None
        lengths = self.headers.get_all('Content-Length', [])
        if not lengths:
            self.send_error(411, 'Content-Length is required')
            return None
        if len(lengths) != 1:
            self.send_error(400, 'Provide exactly one Content-Length')
            return None
        length = lengths[0].strip()
        if not length or any(char not in '0123456789' for char in length):
            self.send_error(400, 'Invalid Content-Length')
            return None
        # Avoid converting arbitrarily long decimal strings to integers.
        length = length.lstrip('0') or '0'
        if len(length) > len(str(MAX_BODY_BYTES)) or int(length) > MAX_BODY_BYTES:
            self.send_error(413)
            return None
        count = int(length)
        try:
            raw = self.rfile.read(count)
        except TimeoutError:
            self.send_error(408, 'Request body timed out')
            return None
        if len(raw) != count:
            self.send_error(400, 'Incomplete request body')
            return None
        return raw

    def do_POST(self):
        if self.path != '/submit':
            self.send_error(404)
            return
        raw = self.read_body()
        if raw is None:
            return
        form = parse_qs(raw.decode('utf-8', 'replace'))
        message = form.get('message', [''])[0]
        print(f'[{self.server.server_port}] received message: {message}',flush=True)
        body = json.dumps({'received': message, 'secure_transport': isinstance(self.connection, ssl.SSLSocket)}).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f'[{self.server.server_port}] {fmt % args}',flush=True)


def run_server(server):
    server.serve_forever(poll_interval=0.1)


def main():
    crt = ROOT / 'certs' / 'demo-server.pem'
    key = ROOT / 'certs' / 'demo-server-key.pem'
    if not crt.exists() or not key.exists():
        raise SystemExit('Missing local certificates. First run: python setup.py')
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.set_alpn_protocols(['http/1.1'])
    ctx.load_cert_chain(certfile=str(crt), keyfile=str(key))
    http_srv = DemoServer(('127.0.0.1', 8000), DemoHandler)
    https_srv = DemoServer(('127.0.0.1', 8443), DemoHandler, tls_context=ctx)
    threading.Thread(target=run_server, args=(http_srv,),daemon=True).start()
    print('HTTP ready:  http://localhost:8000/submit')
    print('HTTPS ready: https://localhost:8443/submit (TLS 1.3 only)')
    print('Listening on local machine only. Press Ctrl+C to stop.')
    try:
        https_srv.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        http_srv.shutdown()
        https_srv.server_close()
        http_srv.server_close()

if __name__ == '__main__':
    main()
