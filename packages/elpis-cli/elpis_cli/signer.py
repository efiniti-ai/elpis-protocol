"""Ed25519 request signing for Elpis Protocol.

Produces X-Elpis-* headers compatible with elpis-proxy, elpis-signer,
and the Pandora Agent SDK.
"""

import base64
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# ARGUS H1 alignment: reject control characters in canonical fields
_SAFE_FIELD_RE = re.compile(r"^[^\n\r\x00-\x1f]+$")


def sign_request(
    private_seed: bytes,
    method: str,
    url: str,
    body: bytes = b"",
) -> Dict[str, str]:
    """Sign an HTTP request with Ed25519.

    Canonical format (identical to elpis-proxy/elpis-signer):
        {method}\\n{url}\\n{body_hash}\\n{timestamp}\\n{nonce}

    Args:
        private_seed: 32-byte Ed25519 private key seed.
        method: HTTP method (GET, POST, etc.).
        url: Full target URL.
        body: Request body bytes.

    Returns:
        Dict of X-Elpis-* headers (Timestamp, Nonce, Signature).
    """
    for name, val in [("method", method), ("url", url)]:
        if not val or not _SAFE_FIELD_RE.match(val):
            raise ValueError(f"sign_request: {name} contains invalid characters")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body).hexdigest()

    canonical = f"{method}\n{url}\n{body_hash}\n{timestamp}\n{nonce}"

    key = Ed25519PrivateKey.from_private_bytes(private_seed)
    signature = key.sign(canonical.encode())
    signature_b64 = base64.b64encode(signature).decode()

    return {
        "X-Elpis-Timestamp": timestamp,
        "X-Elpis-Nonce": nonce,
        "X-Elpis-Signature": signature_b64,
    }
