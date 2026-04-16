"""Tests for elpis_cli.iota_client module."""

import json

import pytest

from elpis_cli.identity import generate_keypair, create_did, build_identity
from elpis_cli.iota_client import (
    derive_iota_address,
    create_iota_did,
    build_verifiable_credential,
    resolve_did,
)


class TestDeriveIotaAddress:
    def test_returns_hex_string(self):
        _, pub = generate_keypair()
        addr = derive_iota_address(pub)
        assert addr.startswith("0x")
        assert len(addr) == 66  # 0x + 64 hex chars

    def test_deterministic(self):
        _, pub = generate_keypair()
        addr1 = derive_iota_address(pub)
        addr2 = derive_iota_address(pub)
        assert addr1 == addr2

    def test_different_keys_different_addresses(self):
        _, pub1 = generate_keypair()
        _, pub2 = generate_keypair()
        assert derive_iota_address(pub1) != derive_iota_address(pub2)

    def test_lowercase_hex(self):
        _, pub = generate_keypair()
        addr = derive_iota_address(pub)
        assert addr == addr.lower()


class TestCreateIotaDid:
    def test_testnet_format(self):
        did = create_iota_did("0x" + "ab" * 32, network="testnet")
        assert did.startswith("did:iota:iota-testnet:0x")
        assert len(did.split(":")[-1]) == 66

    def test_mainnet_format(self):
        did = create_iota_did("0x" + "cd" * 32, network="mainnet")
        assert did.startswith("did:iota:0x")
        assert "iota-testnet" not in did

    def test_lowercase_object_id(self):
        did = create_iota_did("0xABCDEF" + "00" * 29, network="testnet")
        assert "ABCDEF" not in did
        assert "abcdef" in did

    def test_auto_prefix(self):
        did = create_iota_did("ab" * 32, network="testnet")
        assert ":0x" in did


class TestCreateDidWithLedger:
    def test_iota_ledger(self):
        _, pub = generate_keypair()
        did = create_did("testnet", pub, ledger="iota")
        assert did.startswith("did:iota:")

    def test_xrpl_ledger(self):
        _, pub = generate_keypair()
        did = create_did("testnet", pub, ledger="xrpl")
        assert did.startswith("did:xrpl:")

    def test_iota_mainnet(self):
        _, pub = generate_keypair()
        did = create_did("mainnet", pub, ledger="iota")
        assert did.startswith("did:iota:0x")
        assert "testnet" not in did


class TestBuildIdentityWithLedger:
    def test_iota_identity(self):
        seed, pub = generate_keypair()
        identity = build_identity(
            name="test-agent",
            provider="efiniti",
            network="testnet",
            private_seed=seed,
            public_key=pub,
            ledger="iota",
        )
        assert identity["did"].startswith("did:iota:")
        assert identity["ledger"] == "iota"

    def test_xrpl_identity(self):
        seed, pub = generate_keypair()
        identity = build_identity(
            name="test-agent",
            private_seed=seed,
            public_key=pub,
            ledger="xrpl",
        )
        assert identity["did"].startswith("did:xrpl:")
        assert identity["ledger"] == "xrpl"


class TestBuildVerifiableCredential:
    def test_vc_structure(self):
        seed, pub = generate_keypair()
        issuer_did = "did:iota:iota-testnet:0x" + "ab" * 32
        subject_did = "did:iota:iota-testnet:0x" + "cd" * 32

        vc = build_verifiable_credential(
            issuer_did=issuer_did,
            subject_did=subject_did,
            issuer_private_seed=seed,
            claims={"role": "test-agent", "provider": "efiniti.elpis"},
        )

        assert vc["@context"][0] == "https://www.w3.org/2018/credentials/v1"
        assert "ElpisAgentCertificate" in vc["type"]
        assert vc["issuer"] == issuer_did
        assert vc["credentialSubject"]["id"] == subject_did
        assert vc["credentialSubject"]["role"] == "test-agent"

    def test_vc_has_proof(self):
        seed, _ = generate_keypair()
        vc = build_verifiable_credential(
            issuer_did="did:iota:0x" + "ab" * 32,
            subject_did="did:iota:0x" + "cd" * 32,
            issuer_private_seed=seed,
            claims={},
        )
        assert "proof" in vc
        assert vc["proof"]["type"] == "Ed25519Signature2020"
        assert vc["proof"]["proofValue"]

    def test_vc_has_revocation_status(self):
        seed, _ = generate_keypair()
        vc = build_verifiable_credential(
            issuer_did="did:iota:0x" + "ab" * 32,
            subject_did="did:iota:0x" + "cd" * 32,
            issuer_private_seed=seed,
            claims={},
            revocation_index=42,
        )
        assert vc["credentialStatus"]["type"] == "RevocationBitmap2022"
        assert vc["credentialStatus"]["revocationBitmapIndex"] == 42

    def test_vc_deterministic_for_same_input(self):
        seed, _ = generate_keypair()
        issuer = "did:iota:0x" + "ab" * 32
        subject = "did:iota:0x" + "cd" * 32
        claims = {"role": "test"}

        vc1 = build_verifiable_credential(issuer, subject, seed, claims)
        vc2 = build_verifiable_credential(issuer, subject, seed, claims)

        assert vc1["credentialSubject"] == vc2["credentialSubject"]
        assert vc1["issuer"] == vc2["issuer"]


class TestResolveDid:
    @pytest.mark.asyncio
    async def test_resolve_testnet_did(self):
        did = "did:iota:iota-testnet:0x" + "ab" * 32
        doc = await resolve_did(did)
        assert doc is not None
        assert doc["id"] == did
        assert doc["verificationMethod"][0]["type"] == "JsonWebKey"

    @pytest.mark.asyncio
    async def test_resolve_mainnet_did(self):
        did = "did:iota:0x" + "ab" * 32
        doc = await resolve_did(did)
        assert doc is not None
        assert doc["_meta"]["network"] == "mainnet"

    @pytest.mark.asyncio
    async def test_resolve_has_revocation_service(self):
        did = "did:iota:iota-testnet:0x" + "ab" * 32
        doc = await resolve_did(did)
        services = doc["service"]
        revocation = [s for s in services if s["type"] == "RevocationBitmap2022"]
        assert len(revocation) == 1
