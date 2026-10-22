"""Local integration checks: python -m unittest -v test_server."""
import http.client
import json
from pathlib import Path
import runpy
import shutil
import socket
import ssl
import tempfile
import threading
import unittest

from server import DemoHandler, DemoServer


class QuietHandler(DemoHandler):
    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent
        cls.temp = tempfile.TemporaryDirectory(prefix='tls-tests-', dir=root)
        cls.addClassCleanup(cls.temp.cleanup)
        work = Path(cls.temp.name)
        shutil.copyfile(root / 'setup.py', work / 'setup.py')
        runpy.run_path(str(work / 'setup.py'))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(work / 'certs/demo-server.pem',
                                work / 'certs/demo-server-key.pem')
        cls.client_context = ssl.create_default_context(cafile=str(work / 'certs/demo-ca.pem'))
        cls.http = cls.start_server()
        cls.https = cls.start_server(context)

    @classmethod
    def start_server(cls, context=None):
        server = DemoServer(('127.0.0.1', 0), QuietHandler,
                            tls_context=context, connection_timeout=0.5)
        thread = threading.Thread(target=server.serve_forever,
                                  kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()

        cls.addClassCleanup(cleanup)
        return server

    def raw_request(self, headers, body=b'', *, eof=False):
        with socket.create_connection(self.http.server_address, timeout=2) as sock:
            sock.sendall(b'POST /submit HTTP/1.1\r\nHost: localhost\r\n' +
                         headers + b'\r\n\r\n' + body)
            if eof:
                sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(sock)
            response.begin()
            response.read()
            return response.status, response.getheader('Connection')

    def test_invalid_framing(self):
        cases = [
            (b'', 411),
            (b'Content-Length: -1', 400),
            (b'Content-Length: nope', 400),
            (b'Content-Length: +1', 400),
            (b'Content-Length: 0\r\nContent-Length: 0', 400),
            (b'Transfer-Encoding: chunked\r\nContent-Length: 0', 400),
            (b'Content-Length: 4097', 413),
            (b'Content-Length: ' + b'9' * 5000, 413),
        ]
        for headers, status in cases:
            with self.subTest(headers=headers[:80]):
                self.assertEqual(self.raw_request(headers), (status, 'close'))

    def test_partial_body_timeout(self):
        self.assertEqual(self.raw_request(b'Content-Length: 10', b'x'), (408, 'close'))

    def test_truncated_body(self):
        self.assertEqual(self.raw_request(b'Content-Length: 10', b'x', eof=True),
                         (400, 'close'))

    def test_maximum_body(self):
        self.assertEqual(self.raw_request(b'Content-Length: 4096', b'x' * 4096)[0], 200)

    def test_idle_http_connection_closes(self):
        with socket.create_connection(self.http.server_address, timeout=2) as idle:
            self.assertEqual(idle.recv(1), b'')

    def test_idle_tls_does_not_block_verified_client(self):
        with socket.create_connection(self.https.server_address, timeout=2) as idle:
            conn = http.client.HTTPSConnection('localhost', self.https.server_port,
                                               context=self.client_context, timeout=2)
            try:
                conn.connect()
                self.assertEqual(conn.sock.version(), 'TLSv1.3')
                conn.request('POST', '/submit', b'message=test')
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()),
                                 {'received': 'test', 'secure_transport': True})
            finally:
                conn.close()
            self.assertEqual(idle.recv(1), b'')


if __name__ == '__main__':
    unittest.main()
