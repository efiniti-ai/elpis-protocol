"""Elpis CLI configuration and identity file management."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


ELPIS_DIR = Path.home() / ".elpis"
IDENTITY_FILE = ELPIS_DIR / "identity.json"
KEY_FILE = ELPIS_DIR / "private.key"


def ensure_dir() -> Path:
    """Create ~/.elpis/ with restricted permissions if it doesn't exist."""
    ELPIS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    return ELPIS_DIR


def save_identity(identity: Dict[str, Any]) -> Path:
    """Save identity to ~/.elpis/identity.json."""
    ensure_dir()
    IDENTITY_FILE.write_text(json.dumps(identity, indent=2))
    IDENTITY_FILE.chmod(0o600)
    return IDENTITY_FILE


def load_identity() -> Optional[Dict[str, Any]]:
    """Load identity from ~/.elpis/identity.json. Returns None if not found."""
    if not IDENTITY_FILE.exists():
        return None
    try:
        return json.loads(IDENTITY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_private_key(key_hex: str) -> Path:
    """Save private key (hex-encoded) to ~/.elpis/private.key.

    Uses os.open() with explicit permissions to avoid race condition
    where the key file is briefly world-readable with default umask.

    Note:
        The private key is stored in plaintext (hex-encoded).
        TODO: Implement encryption-at-rest (e.g. age/AEAD) before v1.0.
    """
    ensure_dir()
    fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(key_hex)
    return KEY_FILE


def load_private_key() -> Optional[str]:
    """Load private key hex from ~/.elpis/private.key."""
    if not KEY_FILE.exists():
        return None
    try:
        return KEY_FILE.read_text().strip()
    except OSError:
        return None


def identity_exists() -> bool:
    """Check if an identity has been initialized."""
    return IDENTITY_FILE.exists() and KEY_FILE.exists()
