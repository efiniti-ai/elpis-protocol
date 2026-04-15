"""Tests for elpis_cli.identity module."""

import pytest

from elpis_cli.identity import (
    build_identity,
    create_did,
    generate_keypair,
    load_keypair_from_file,
)


class TestGenerateKeypair:
    def test_returns_32_byte_seed_and_pubkey(self):
        seed, pub = generate_keypair()
        assert len(seed) == 32
        assert len(pub) == 32

    def test_different_calls_produce_different_keys(self):
        seed1, _ = generate_keypair()
        seed2, _ = generate_keypair()
        assert seed1 != seed2


class TestCreateDid:
    def test_did_format(self):
        _, pub = generate_keypair()
        did = create_did("testnet", pub)
        assert did.startswith("did:xrpl:")
        assert "#" in did

    def test_fragment_is_opaque(self):
        _, pub = generate_keypair()
        did = create_did("testnet", pub)
        fragment = did.split("#")[1]
        assert len(fragment) == 8

    def test_did_is_deterministic(self):
        _, pub = generate_keypair()
        did1 = create_did("testnet", pub)
        did2 = create_did("testnet", pub)
        assert did1 == did2


class TestBuildIdentity:
    def test_identity_fields(self):
        seed, pub = generate_keypair()
        identity = build_identity(
            name="test-agent",
            provider="test",
            role="worker",
            network="testnet",
            private_seed=seed,
            public_key=pub,
        )
        assert identity["name"] == "test-agent"
        assert identity["provider"] == "test"
        assert identity["version"] == "1.0"
        assert identity["did"].startswith("did:xrpl:")
        assert identity["public_key"] == pub.hex()
        assert identity["cert_hash"]

    def test_identity_with_provided_did(self):
        seed, pub = generate_keypair()
        custom_did = "did:xrpl:custom#fragment"
        identity = build_identity(
            name="test", private_seed=seed, public_key=pub, did=custom_did
        )
        assert identity["did"] == custom_did


class TestLoadKeypairFromFile:
    def test_load_hex_key(self, tmp_path):
        seed, _ = generate_keypair()
        key_file = tmp_path / "test.key"
        key_file.write_text(seed.hex())
        loaded_seed, loaded_pub = load_keypair_from_file(str(key_file))
        assert loaded_seed == seed

    def test_invalid_hex_raises(self, tmp_path):
        key_file = tmp_path / "bad.key"
        key_file.write_text("not-hex")
        with pytest.raises((ValueError, Exception)):
            load_keypair_from_file(str(key_file))
