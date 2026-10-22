"""Generate a LOCAL test CA and a localhost TLS certificate (not production PKI)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'certs'
OUT.mkdir(exist_ok=True)
now = datetime.now(timezone.utc)

def pem_priv(path: Path, key):
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))

def pem_cert(path: Path, cert):
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'ACG CA1 LOCAL TEST CA')])
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=30))
    .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
    .add_extension(x509.KeyUsage(digital_signature=False,content_commitment=False,key_encipherment=False,
                                 data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,
                                 encipher_only=False,decipher_only=False),critical=True)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
    .sign(ca_key, hashes.SHA256())
)
server_key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
server_cert = (
    x509.CertificateBuilder()
    .subject_name(server_name).issuer_name(ca_name).public_key(server_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=30))
    .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
    .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False)
    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
    .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,
                                 data_encipherment=False,key_agreement=False,key_cert_sign=False,crl_sign=False,
                                 encipher_only=False,decipher_only=False),critical=True)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),critical=False)
    .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
    .sign(ca_key, hashes.SHA256())
)
pem_priv(OUT / 'demo-ca-key.pem', ca_key)
pem_cert(OUT / 'demo-ca.pem', ca_cert)
pem_priv(OUT / 'demo-server-key.pem', server_key)
pem_cert(OUT / 'demo-server.pem', server_cert)
print('Generated LOCAL ONLY certificates in:', OUT)
print('Demo CA certificate: certs/demo-ca.pem')
print('Server certificate: certs/demo-server.pem')
print('Never use this local CA or its private keys for real websites.')
