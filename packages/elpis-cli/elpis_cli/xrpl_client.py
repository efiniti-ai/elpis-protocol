"""XRPL integration for full Elpis identity chain.

Supports both Testnet (auto-funded, zero interaction) and Mainnet
(user wallet, cost preview, confirmation per TX) modes.

Transaction chain: DIDSet -> MPTokenIssuanceCreate -> CredentialCreate.

Requires xrpl-py for client-side transaction signing (XRPL public
servers no longer support server-side signing).
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("elpis.xrpl")

# Lazy imports for xrpl-py (optional dependency)
_xrpl_available = False
try:
    from xrpl.wallet import Wallet
    from xrpl.models.transactions import (
        DIDSet,
        MPTokenIssuanceCreate,
        CredentialCreate,
    )
    from xrpl.transaction import sign as xrpl_sign_tx
    _xrpl_available = True
except ImportError:
    pass

# Network configs
NETWORKS = {
    "testnet": {
        "faucet": "https://faucet.altnet.rippletest.net/accounts",
        "rpc": "https://s.altnet.rippletest.net:51234",
        "wss": "wss://s.altnet.rippletest.net:51233",
        "reserve_base": 10,   # XRP base reserve
        "reserve_inc": 2,     # XRP owner reserve increment per object
    },
    "mainnet": {
        "faucet": "",
        "rpc": "https://xrplcluster.com",
        "wss": "wss://xrplcluster.com",
        "reserve_base": 10,
        "reserve_inc": 2,
    },
}

# TX fees (drops)
TX_FEE_DROPS = 12
DROPS_PER_XRP = 1_000_000

# Faucet retry config
FAUCET_MAX_RETRIES = 3
FAUCET_RETRY_DELAY = 2.0
FUNDING_POLL_INTERVAL = 2.0
FUNDING_POLL_MAX = 15


async def _rpc(client, rpc_url: str, method: str, params: list) -> Dict[str, Any]:
    """Submit a JSON-RPC call to XRPL."""
    resp = await client.post(
        rpc_url,
        json={"method": method, "params": params},
    )
    resp.raise_for_status()
    return resp.json().get("result", {})


async def _get_sequence(client, rpc_url: str, address: str) -> int:
    """Get current account sequence number (fresh, for each TX)."""
    result = await _rpc(client, rpc_url, "account_info", [{
        "account": address,
        "ledger_index": "current",
    }])
    return result.get("account_data", {}).get("Sequence", 0)


async def _get_balance(client, rpc_url: str, address: str) -> float:
    """Get account XRP balance."""
    result = await _rpc(client, rpc_url, "account_info", [{
        "account": address,
        "ledger_index": "validated",
    }])
    balance_drops = int(result.get("account_data", {}).get("Balance", "0"))
    return balance_drops / DROPS_PER_XRP


async def _submit_tx(
    client, rpc_url: str, tx: Dict[str, Any], secret: str
) -> Tuple[str, str, str]:
    """Sign locally and submit a transaction. Returns (engine_result, tx_hash, error_msg).

    Uses xrpl-py for client-side signing since XRPL public servers
    no longer support server-side signing via 'secret' parameter.
    """
    if not _xrpl_available:
        return "", "", "xrpl-py not installed. Install with: pip install elpis-cli[xrpl]"

    try:
        wallet = Wallet.from_seed(secret)

        # Map our tx dict to xrpl-py model
        tx_type = tx["TransactionType"]
        common = {
            "account": tx["Account"],
            "fee": str(tx.get("Fee", TX_FEE_DROPS)),
            "sequence": tx.get("Sequence", 0),
        }

        if tx_type == "DIDSet":
            tx_model = DIDSet(**common, uri=tx.get("URI", ""), data=tx.get("Data", ""))
        elif tx_type == "MPTokenIssuanceCreate":
            mpt_kwargs = {
                **common,
                "flags": tx.get("Flags", 2),
                "maximum_amount": tx.get("MaximumAmount", "1"),
                "asset_scale": tx.get("AssetScale", 0),
            }
            # Only include transfer_fee when non-zero (xrpl-py validates flag dependency)
            if tx.get("TransferFee", 0):
                mpt_kwargs["transfer_fee"] = tx["TransferFee"]
            tx_model = MPTokenIssuanceCreate(**mpt_kwargs)
        elif tx_type == "CredentialCreate":
            tx_model = CredentialCreate(
                **common,
                subject=tx.get("Subject", tx["Account"]),
                credential_type=tx.get("CredentialType", ""),
                uri=tx.get("URI", ""),
            )
        else:
            return "", "", f"Unsupported transaction type: {tx_type}"

        signed = xrpl_sign_tx(tx_model, wallet)
        result = await _rpc(client, rpc_url, "submit", [{"tx_blob": signed.blob()}])

    except Exception as exc:
        return "", "", str(exc)

    engine_result = result.get("engine_result", "")
    tx_hash = result.get("tx_json", {}).get("hash", "")
    error_msg = result.get("engine_result_message", "")
    return engine_result, tx_hash, error_msg


async def _fund_account(client, network_cfg: dict) -> Optional[Dict[str, str]]:
    """Request a funded testnet account with retry.

    Returns dict with 'address' and 'secret', or None on failure.
    """
    for attempt in range(1, FAUCET_MAX_RETRIES + 1):
        try:
            resp = await client.post(network_cfg["faucet"])
            if resp.status_code != 200:
                logger.warning(
                    "Faucet attempt %d/%d: HTTP %d",
                    attempt, FAUCET_MAX_RETRIES, resp.status_code,
                )
                await asyncio.sleep(FAUCET_RETRY_DELAY * attempt)
                continue

            data = resp.json()

            # Faucet response format varies -- handle both layouts
            account = data.get("account", data)
            address = account.get("address", account.get("classicAddress", ""))
            # seed/secret may be at root level or inside account
            secret = (
                account.get("secret")
                or account.get("seed")
                or data.get("secret")
                or data.get("seed")
                or ""
            )

            if not address or not secret:
                logger.warning(
                    "Faucet attempt %d/%d: incomplete data (keys: %s)",
                    attempt, FAUCET_MAX_RETRIES, list(account.keys()),
                )
                await asyncio.sleep(FAUCET_RETRY_DELAY * attempt)
                continue

            # Poll until funded
            funded = False
            for _ in range(FUNDING_POLL_MAX):
                await asyncio.sleep(FUNDING_POLL_INTERVAL)
                try:
                    result = await _rpc(client, network_cfg["rpc"], "account_info", [{
                        "account": address,
                        "ledger_index": "validated",
                    }])
                    if result.get("account_data"):
                        funded = True
                        break
                except Exception:
                    pass

            if funded:
                logger.info("Testnet account funded: %s", address)
                return {"address": address, "secret": secret}
            else:
                logger.warning(
                    "Faucet attempt %d/%d: funding timeout for %s",
                    attempt, FAUCET_MAX_RETRIES, address,
                )

        except Exception as exc:
            logger.warning(
                "Faucet attempt %d/%d: %s",
                attempt, FAUCET_MAX_RETRIES, exc,
            )
            await asyncio.sleep(FAUCET_RETRY_DELAY * attempt)

    return None


async def _build_didset_tx(address: str, did: str, public_key_hex: str) -> Dict:
    """Build DIDSet transaction body."""
    return {
        "TransactionType": "DIDSet",
        "Account": address,
        "Fee": str(TX_FEE_DROPS),
        "URI": did.encode().hex().upper()[:256],
        "Data": public_key_hex.upper()[:256],
    }


async def _build_mpt_tx(address: str) -> Dict:
    """Build MPTokenIssuanceCreate transaction body."""
    return {
        "TransactionType": "MPTokenIssuanceCreate",
        "Account": address,
        "Fee": str(TX_FEE_DROPS),
        "Flags": 2,  # lsfMPTCanTransfer
        "MaximumAmount": "1",
        "AssetScale": 0,
        "TransferFee": 0,
    }


async def _build_credential_tx(address: str, did: str) -> Dict:
    """Build CredentialCreate (XLS-70) transaction body."""
    return {
        "TransactionType": "CredentialCreate",
        "Account": address,
        "Subject": address,
        "Fee": str(TX_FEE_DROPS),
        "CredentialType": "ElpisAgentIdentity".encode().hex().upper(),
        "URI": did.encode().hex().upper()[:256],
    }


# TX descriptions for user confirmation
TX_DESCRIPTIONS = {
    "DIDSet": "Anchor DID on XRPL Ledger (creates DID Object, +2 XRP reserve)",
    "MPTokenIssuanceCreate": "Mint Identity Token (creates MPT Object, +2 XRP reserve)",
    "CredentialCreate": "Issue on-chain credential (creates Credential Object, +2 XRP reserve)",
}


async def _execute_tx_chain(
    client,
    rpc_url: str,
    address: str,
    secret: str,
    transactions: List[Tuple[str, Dict]],
    confirm_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Execute a chain of transactions with optional per-TX confirmation.

    Args:
        client: httpx AsyncClient.
        rpc_url: XRPL JSON-RPC URL.
        address: Account address.
        secret: Account secret for signing.
        transactions: List of (step_name, tx_body) tuples.
        confirm_fn: Optional sync callback(step_name, tx_type, fee_xrp, reserve_xrp) -> bool.
            If None or returns True, TX is submitted. If False, TX is skipped.

    Returns:
        Dict with steps results.
    """
    steps: Dict[str, Dict] = {}

    for step_name, tx_body in transactions:
        tx_type = tx_body["TransactionType"]
        fee_xrp = int(tx_body.get("Fee", TX_FEE_DROPS)) / DROPS_PER_XRP
        reserve_xrp = 2.0  # Owner reserve per object

        # Mainnet mode: confirm each TX
        if confirm_fn:
            proceed = confirm_fn(step_name, tx_type, fee_xrp, reserve_xrp)
            if not proceed:
                steps[step_name] = {"success": False, "tx_hash": "", "skipped": True}
                logger.info("TX %s skipped by user", step_name)
                continue

        # Fresh sequence for each TX (MEDIUM fix from pandora-coder review)
        sequence = await _get_sequence(client, rpc_url, address)
        if not sequence:
            steps[step_name] = {"success": False, "tx_hash": "", "error": "No sequence"}
            continue

        tx_body["Sequence"] = sequence

        try:
            engine_result, tx_hash, error_msg = await _submit_tx(
                client, rpc_url, tx_body, secret,
            )

            success = engine_result in ("tesSUCCESS", "terQUEUED")
            steps[step_name] = {
                "success": success,
                "tx_hash": tx_hash,
                "engine_result": engine_result,
            }
            if not success:
                steps[step_name]["error"] = error_msg

            logger.info(
                "%s %s: %s (hash=%s)",
                step_name, "OK" if success else "FAILED",
                engine_result, tx_hash[:12] if tx_hash else "",
            )

            # Pause between TXs
            await asyncio.sleep(1)

        except Exception as exc:
            steps[step_name] = {"success": False, "tx_hash": "", "error": str(exc)}
            logger.warning("%s ERROR: %s", step_name, exc)

    return steps


async def register_did_testnet(
    did: str,
    public_key_hex: str,
    name: str = "",
) -> Optional[Dict[str, Any]]:
    """Register a full Elpis identity on XRPL Testnet.

    Complete chain: Faucet -> DIDSet -> MPT -> Credential.
    Zero interaction, auto-funded.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not available")
        return None

    network_cfg = NETWORKS["testnet"]
    result: Dict[str, Any] = {
        "registered": False,
        "network": "testnet",
        "did": did,
        "address": "",
        "steps": {},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            account = await _fund_account(client, network_cfg)
            if not account:
                result["error"] = "Faucet failed after retries"
                return result

            address = account["address"]
            secret = account["secret"]
            result["address"] = address

            # Build TX chain
            transactions = [
                ("didset", await _build_didset_tx(address, did, public_key_hex)),
                ("mpt", await _build_mpt_tx(address)),
                ("credential", await _build_credential_tx(address, did)),
            ]

            steps = await _execute_tx_chain(
                client, network_cfg["rpc"], address, secret, transactions,
            )
            result["steps"] = steps

            # Extract hashes
            if steps.get("didset", {}).get("tx_hash"):
                result["tx_hash"] = steps["didset"]["tx_hash"]
            if steps.get("mpt", {}).get("tx_hash"):
                result["mpt_tx_hash"] = steps["mpt"]["tx_hash"]
            if steps.get("credential", {}).get("tx_hash"):
                result["credential_tx_hash"] = steps["credential"]["tx_hash"]

            result["registered"] = steps.get("didset", {}).get("success", False)
            return result

    except Exception as exc:
        logger.warning("XRPL registration failed: %s", exc)
        result["error"] = str(exc)
        return result if result.get("address") else None


async def register_did_mainnet(
    did: str,
    public_key_hex: str,
    name: str = "",
    wallet_address: str = "",
    wallet_secret: str = "",
    confirm_fn: Optional[Callable] = None,
) -> Optional[Dict[str, Any]]:
    """Register a full Elpis identity on XRPL Mainnet.

    User provides wallet credentials. Each TX requires confirmation
    via confirm_fn showing fee + reserve cost.

    Args:
        did: DID to register.
        public_key_hex: Hex-encoded Ed25519 public key.
        name: Display name.
        wallet_address: XRPL mainnet r-address.
        wallet_secret: Wallet secret for signing.
        confirm_fn: Callback(step_name, tx_type, fee_xrp, reserve_xrp) -> bool.

    Returns:
        Registration result dict or None on failure.
    """
    try:
        import httpx
    except ImportError:
        return None

    if not wallet_address or not wallet_secret:
        return {"registered": False, "error": "Wallet address and secret required for mainnet"}

    network_cfg = NETWORKS["mainnet"]
    result: Dict[str, Any] = {
        "registered": False,
        "network": "mainnet",
        "did": did,
        "address": wallet_address,
        "steps": {},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Pre-flight: check balance
            balance = await _get_balance(client, network_cfg["rpc"], wallet_address)
            result["balance_xrp"] = balance

            # Estimate total cost: 3 TXs * 12 drops fee + 3 * 2 XRP reserve = ~6.000036 XRP
            total_fee = 3 * TX_FEE_DROPS / DROPS_PER_XRP
            total_reserve = 3 * 2.0  # 3 objects * 2 XRP owner reserve
            result["estimated_cost"] = {
                "fees_xrp": total_fee,
                "reserve_xrp": total_reserve,
                "total_xrp": total_fee + total_reserve,
            }

            if balance < total_reserve + network_cfg["reserve_base"] + total_fee:
                result["error"] = (
                    f"Insufficient balance: {balance:.2f} XRP. "
                    f"Need ~{total_reserve + network_cfg['reserve_base'] + total_fee:.2f} XRP "
                    f"(base reserve {network_cfg['reserve_base']} + "
                    f"owner reserve {total_reserve} + fees {total_fee:.6f})"
                )
                return result

            transactions = [
                ("didset", await _build_didset_tx(wallet_address, did, public_key_hex)),
                ("mpt", await _build_mpt_tx(wallet_address)),
                ("credential", await _build_credential_tx(wallet_address, did)),
            ]

            steps = await _execute_tx_chain(
                client, network_cfg["rpc"], wallet_address, wallet_secret,
                transactions, confirm_fn=confirm_fn,
            )
            result["steps"] = steps

            if steps.get("didset", {}).get("tx_hash"):
                result["tx_hash"] = steps["didset"]["tx_hash"]
            if steps.get("mpt", {}).get("tx_hash"):
                result["mpt_tx_hash"] = steps["mpt"]["tx_hash"]
            if steps.get("credential", {}).get("tx_hash"):
                result["credential_tx_hash"] = steps["credential"]["tx_hash"]

            result["registered"] = steps.get("didset", {}).get("success", False)
            return result

    except Exception as exc:
        logger.warning("XRPL mainnet registration failed: %s", exc)
        result["error"] = str(exc)
        return result
