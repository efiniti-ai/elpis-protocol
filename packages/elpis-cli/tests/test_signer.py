"""Tests for elpis_cli.signer module."""

import base64

import pytest

from elpis_cli.identity import generate_keypair
from elpis_cli.signer import sign_request


class TestSignRequest:
    def setup_method(self):
        self.seed, self.pub = generate_keypair()

    def test_returns_three_headers(self):
        headers = sign_request(self.seed, "GET", "https://example.com")
        assert "X-Elpis-Timestamp" in headers
        assert "X-Elpis-Nonce" in headers
        assert "X-Elpis-Signature" in headers
        assert len(headers) == 3

    def test_timestamp_ends_with_z(self):
        headers = sign_request(self.seed, "GET", "https://example.com")
        assert headers["X-Elpis-Timestamp"].endswith("Z")

    def test_signature_is_base64(self):
        headers = sign_request(self.seed, "GET", "https://example.com")
        sig = headers["X-Elpis-Signature"]
        decoded = base64.b64decode(sig)
        assert len(decoded) == 64  # Ed25519 signature is 64 bytes

    def test_different_requests_different_nonces(self):
        h1 = sign_request(self.seed, "GET", "https://a.com")
        h2 = sign_request(self.seed, "GET", "https://b.com")
        assert h1["X-Elpis-Nonce"] != h2["X-Elpis-Nonce"]

    def test_rejects_control_chars_in_method(self):
        with pytest.raises(ValueError):
            sign_request(self.seed, "GET\x00", "https://example.com")

    def test_rejects_empty_method(self):
        with pytest.raises(ValueError):
            sign_request(self.seed, "", "https://example.com")

    def test_signature_verifiable(self):
        """Verify that the signature can be verified with the public key."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        import hashlib

        headers = sign_request(self.seed, "GET", "https://example.com", b"hello")

        # Reconstruct canonical string
        body_hash = hashlib.sha256(b"hello").hexdigest()
        canonical = f"GET\nhttps://example.com\n{body_hash}\n{headers['X-Elpis-Timestamp']}\n{headers['X-Elpis-Nonce']}"

        # Verify with public key
        key = Ed25519PrivateKey.from_private_bytes(self.seed)
        pub = key.public_key()
        sig = base64.b64decode(headers["X-Elpis-Signature"])

        # Should not raise
        pub.verify(sig, canonical.encode())
