"""Ed25519 identity management for Elpis Protocol."""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> Tuple[bytes, bytes]:
    """Generate an Ed25519 keypair.

    Returns:
        (private_seed_32bytes, public_key_32bytes)
    """
    private_key = Ed25519PrivateKey.generate()
    private_seed = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_seed, public_key


def load_keypair_from_file(key_path: str) -> Tuple[bytes, bytes]:
    """Load an existing Ed25519 private key from a file.

    Supports hex-encoded raw seed (64 hex chars) or PEM format.

    Args:
        key_path: Path to the key file.

    Returns:
        (private_seed_32bytes, public_key_32bytes)
    """
    with open(key_path, "r") as f:
        content = f.read().strip()

    if content.startswith("-----BEGIN"):
        # PEM format
        private_key = serialization.load_pem_private_key(
            content.encode(), password=None
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Key file is not an Ed25519 key")
    else:
        # Hex-encoded raw seed
        seed = bytes.fromhex(content)
        if len(seed) != 32:
            raise ValueError(f"Expected 32-byte seed, got {len(seed)} bytes")
        private_key = Ed25519PrivateKey.from_private_bytes(seed)

    private_seed = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_seed, public_key


def create_did(network: str = "testnet", public_key: bytes = b"", ledger: str = "iota") -> str:
    """Create a DID from a public key.

    Supports two ledger types:
    - iota: did:iota:{network}:{object_id} (derived from public key hash)
    - xrpl: did:xrpl:{nanoid}#{fragment} (legacy PoC format)

    Args:
        network: Network (testnet, mainnet).
        public_key: 32-byte Ed25519 public key.
        ledger: Ledger type ("iota" or "xrpl").

    Returns:
        DID string.
    """
    if ledger == "iota":
        from .iota_client import derive_iota_address
        object_id = derive_iota_address(public_key)
        if network == "mainnet":
            return f"did:iota:{object_id}"
        return f"did:iota:iota-testnet:{object_id}"

    # Legacy XRPL format
    key_hash = hashlib.sha256(public_key).hexdigest()[:8]
    fragment = hashlib.sha256(public_key + b"fragment").hexdigest()[:8]
    return f"did:xrpl:{key_hash}#{fragment}"


def build_identity(
    name: str,
    provider: str = "",
    role: str = "",
    network: str = "testnet",
    private_seed: bytes = b"",
    public_key: bytes = b"",
    did: str = "",
    ledger: str = "iota",
) -> Dict:
    """Build an identity document.

    Args:
        name: Agent/user display name.
        provider: Provider name (e.g. "efiniti").
        role: Role description.
        network: Network (testnet, mainnet).
        private_seed: Raw 32-byte private key seed.
        public_key: Raw 32-byte public key.
        did: Pre-generated DID (or auto-generated from public_key).
        ledger: Ledger type ("iota" or "xrpl").

    Returns:
        Identity dict suitable for JSON serialization.
    """
    if not did:
        did = create_did(network, public_key, ledger=ledger)

    return {
        "version": "1.0",
        "did": did,
        "name": name,
        "provider": provider,
        "role": role,
        "network": network,
        "ledger": ledger,
        "public_key": public_key.hex(),
        "cert_hash": hashlib.sha256(public_key).hexdigest()[:16],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
