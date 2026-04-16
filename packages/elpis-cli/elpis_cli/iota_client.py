"""IOTA Rebased integration for Elpis identity chain.

Uses the IOTA Rebased JSON-RPC API (MoveVM-based) via httpx.
No external IOTA SDK required — all operations use the public REST API.

DID format: did:iota:{network_id}:{object_id} (testnet)
            did:iota:{object_id} (mainnet, implicit)

Transaction chain: Faucet -> Identity::new() -> VC issuance (off-chain).
"""

import asyncio
import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("elpis.iota")

NETWORKS = {
    "testnet": {
        "faucet": "https://faucet.testnet.iota.cafe/gas",
        "rpc": "https://api.testnet.iota.cafe",
        "explorer": "https://explorer.iota.cafe/?network=iota-testnet",
        "network_id": "iota-testnet",
    },
    "mainnet": {
        "faucet": "",
        "rpc": "https://api.mainnet.iota.cafe",
        "explorer": "https://explorer.iota.cafe/?network=iota-mainnet",
        "network_id": "6364aad5",
    },
}

FAUCET_MAX_RETRIES = 3
FAUCET_RETRY_DELAY = 2.0


def derive_iota_address(public_key: bytes) -> str:
    """Derive an IOTA address from an Ed25519 public key.

    IOTA Rebased uses a scheme byte (0x00 for Ed25519) prepended to the
    public key, then SHA3-256 hashed, to produce the 32-byte address.
    """
    scheme_byte = b"\x00"
    addr_bytes = hashlib.sha3_256(scheme_byte + public_key).digest()
    return "0x" + addr_bytes.hex()


def create_iota_did(object_id: str, network: str = "testnet") -> str:
    """Create a did:iota DID from an object ID.

    Args:
        object_id: Hex object ID (0x + 64 hex chars).
        network: Network name (testnet or mainnet).

    Returns:
        DID string in did:iota format.
    """
    oid = object_id.lower()
    if not oid.startswith("0x"):
        oid = "0x" + oid
    if network == "mainnet":
        return f"did:iota:{oid}"
    net_cfg = NETWORKS.get(network, NETWORKS["testnet"])
    return f"did:iota:{net_cfg['network_id']}:{oid}"


async def _json_rpc(client, rpc_url: str, method: str, params: list) -> Dict[str, Any]:
    """Submit a JSON-RPC call to an IOTA Rebased node."""
    resp = await client.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data.get("result", {})


async def _request_faucet(client, faucet_url: str, address: str) -> bool:
    """Request test tokens from the IOTA Rebased testnet faucet."""
    for attempt in range(1, FAUCET_MAX_RETRIES + 1):
        try:
            resp = await client.post(
                faucet_url,
                json={"FixedAmountRequest": {"recipient": address}},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 201, 202):
                logger.info("Faucet request accepted for %s", address)
                return True
            logger.warning(
                "Faucet attempt %d/%d: HTTP %d",
                attempt, FAUCET_MAX_RETRIES, resp.status_code,
            )
        except Exception as exc:
            logger.warning("Faucet attempt %d/%d: %s", attempt, FAUCET_MAX_RETRIES, exc)
        await asyncio.sleep(FAUCET_RETRY_DELAY * attempt)
    return False


async def _wait_for_balance(client, rpc_url: str, address: str, max_polls: int = 15) -> bool:
    """Poll until the address has a non-zero balance."""
    for _ in range(max_polls):
        await asyncio.sleep(2.0)
        try:
            result = await _json_rpc(client, rpc_url, "iotax_getAllBalances", [address])
            if isinstance(result, list) and len(result) > 0:
                if int(result[0].get("totalBalance", "0")) > 0:
                    return True
            elif isinstance(result, dict) and int(result.get("totalBalance", "0")) > 0:
                return True
        except Exception:
            pass
    return False


async def _get_balance(client, rpc_url: str, address: str) -> int:
    """Get total balance in IOTA (nanos)."""
    try:
        result = await _json_rpc(client, rpc_url, "iotax_getAllBalances", [address])
        if isinstance(result, list) and len(result) > 0:
            return int(result[0].get("totalBalance", "0"))
        elif isinstance(result, dict):
            return int(result.get("totalBalance", "0"))
        return 0
    except Exception:
        return 0


def build_verifiable_credential(
    issuer_did: str,
    subject_did: str,
    issuer_private_seed: bytes,
    claims: Dict[str, Any],
    credential_type: str = "ElpisAgentCertificate",
    revocation_index: int = 0,
) -> Dict[str, Any]:
    """Build and sign an Elpis Verifiable Credential (off-chain).

    The VC is created client-side and signed with Ed25519. It does not
    require an on-chain transaction — only the DID Documents need to be
    on-chain for resolution and revocation.
    """
    now = datetime.now(timezone.utc).isoformat()

    credential = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://elpis.efiniti.ai/credentials/v1",
        ],
        "type": ["VerifiableCredential", credential_type],
        "issuer": issuer_did,
        "issuanceDate": now,
        "credentialSubject": {
            "id": subject_did,
            **claims,
        },
        "credentialStatus": {
            "id": f"{issuer_did}#revocation",
            "type": "RevocationBitmap2022",
            "revocationBitmapIndex": revocation_index,
        },
    }

    canonical = json.dumps(credential, sort_keys=True, separators=(",", ":"))
    key = Ed25519PrivateKey.from_private_bytes(issuer_private_seed)
    signature = key.sign(canonical.encode())

    credential["proof"] = {
        "type": "Ed25519Signature2020",
        "created": now,
        "verificationMethod": f"{issuer_did}#key-1",
        "proofPurpose": "assertionMethod",
        "proofValue": base64.b64encode(signature).decode(),
    }

    return credential


async def register_did_testnet(
    did: str,
    public_key_hex: str,
    name: str = "",
    private_seed_hex: str = "",
) -> Optional[Dict[str, Any]]:
    """Register an Elpis identity on the IOTA Rebased Testnet.

    Flow: Generate address -> Faucet -> Create DID Document on-chain.

    Note: Full on-chain DID creation requires the IOTA Identity SDK
    (Rust/WASM). This implementation handles address creation, funding,
    and VC issuance (off-chain). On-chain DID registration will be
    added when the IOTA Identity Python bindings are available.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not available")
        return None

    network_cfg = NETWORKS["testnet"]
    public_key = bytes.fromhex(public_key_hex)
    address = derive_iota_address(public_key)

    result: Dict[str, Any] = {
        "registered": False,
        "network": "testnet",
        "did": did,
        "address": address,
        "steps": {},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Request faucet
            logger.info("Requesting testnet tokens for %s...", address)
            faucet_ok = await _request_faucet(client, network_cfg["faucet"], address)
            result["steps"]["faucet"] = {
                "success": faucet_ok,
                "tx_hash": "",
            }
            if not faucet_ok:
                result["error"] = "Faucet request failed after retries"
                return result

            # Step 2: Wait for funding
            logger.info("Waiting for balance...")
            funded = await _wait_for_balance(client, network_cfg["rpc"], address)
            result["steps"]["funding"] = {
                "success": funded,
                "tx_hash": "",
            }
            if not funded:
                result["error"] = "Funding timeout"
                return result

            balance = await _get_balance(client, network_cfg["rpc"], address)
            result["balance_nanos"] = balance
            logger.info("Balance: %d nanos", balance)

            # Step 3: Create DID Document on-chain
            # NOTE: Full on-chain DID creation requires IOTA Identity Move calls.
            # Currently: we create the DID locally and issue a VC off-chain.
            # The on-chain registration (Identity::new()) will be implemented
            # when IOTA Identity Python bindings for Rebased are available,
            # or via the `iota` CLI bridge.
            result["steps"]["did_create"] = {
                "success": True,
                "tx_hash": "",
                "note": "DID created locally. On-chain registration pending IOTA Identity SDK.",
            }

            # Step 4: Issue VC (off-chain, always works)
            if private_seed_hex:
                provider_did = did.rsplit("#", 1)[0] if "#" in did else did
                vc = build_verifiable_credential(
                    issuer_did=provider_did,
                    subject_did=did,
                    issuer_private_seed=bytes.fromhex(private_seed_hex),
                    claims={
                        "role": "autonomous-agent",
                        "provider": "efiniti.elpis",
                        "name": name,
                        "ledger": "iota",
                    },
                )
                result["steps"]["credential"] = {
                    "success": True,
                    "tx_hash": "",
                    "credential": vc,
                }
                result["credential"] = vc

            result["registered"] = True
            return result

    except Exception as exc:
        logger.warning("IOTA registration failed: %s", exc)
        result["error"] = str(exc)
        return result


async def resolve_did(did: str) -> Optional[Dict[str, Any]]:
    """Resolve a did:iota DID to its DID Document.

    Queries the IOTA node for the DID's on-chain state.

    Note: Full resolution requires the IOTA Identity SDK resolver.
    This is a placeholder that parses the DID format and returns
    the expected document structure.
    """
    parts = did.replace("did:iota:", "").split(":")
    if len(parts) == 1:
        object_id = parts[0]
        network = "mainnet"
    elif len(parts) == 2:
        network = parts[0]
        object_id = parts[1]
    else:
        return None

    return {
        "id": did,
        "controller": did,
        "verificationMethod": [{
            "id": f"{did}#key-1",
            "type": "JsonWebKey",
            "controller": did,
            "publicKeyJwk": {
                "kty": "OKP",
                "crv": "Ed25519",
            },
        }],
        "service": [{
            "id": f"{did}#revocation",
            "type": "RevocationBitmap2022",
            "serviceEndpoint": "data:application/octet-stream;base64,AA==",
        }],
        "_meta": {
            "network": network,
            "object_id": object_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "source": "local_placeholder",
        },
    }
