"""Send identical HTTP / TLS 1.3 POST messages and optionally log TLS session secrets."""
import argparse
import http.client
import ssl
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
MESSAGE = 'ACG_SECRET_2026'  # Fake classroom test message; never real secrets.


def main():
    p = argparse.ArgumentParser(description='Local HTTP vs HTTPS TLS 1.3 demonstration')
    p.add_argument('mode', choices=['http', 'https', 'untrusted'])
    args = p.parse_args()
    body = urlencode({'message': MESSAGE, 'source': 'ACG_CA1'}).encode('ascii')
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Connection':'close'}
    if args.mode == 'http':
        conn = http.client.HTTPConnection('localhost', 8000, timeout=5)
    else:
        if args.mode == 'https':
            context = ssl.create_default_context(cafile=str(ROOT / 'certs' / 'demo-ca.pem'))
            # Session secrets are ONLY for classroom research on test traffic.
            context.keylog_filename = str(ROOT / 'tls-session-keys.log')
        else:
            context = ssl.create_default_context()  # Does NOT trust our private local CA.
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.set_alpn_protocols(['http/1.1'])
        conn = http.client.HTTPSConnection('localhost', 8443, timeout=5, context=context)
    print(f'Mode: {args.mode} | Message: {MESSAGE}')
    try:
        conn.connect()
        if args.mode != 'http':
            print('Negotiated protocol:', conn.sock.version())
            print('Cipher:', conn.sock.cipher()[0])
        conn.request('POST', '/submit', body=body, headers=headers)
        result = conn.getresponse()
        print('HTTP status:', result.status)
        print('Server response:', result.read().decode())
        if args.mode == 'https':
            print('TLS session secrets were logged to tls-session-keys.log (LOCAL TEST ONLY)')
    except ssl.SSLCertVerificationError as e:
        print('Expected verification failure: demo CA is NOT in system trust store.')
        print(type(e).__name__ + ':', e)
        if args.mode != 'untrusted':
            raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
