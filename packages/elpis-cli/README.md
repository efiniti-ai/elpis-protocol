# elpis-cli

Cryptographic identity for AI agents. One command, 30 seconds, on-chain.

**Elpis** gives every AI agent a verifiable identity: an Ed25519 keypair, a DID anchored on the XRP Ledger, an identity token, and an on-chain credential. No accounts, no API keys, no central authority.

```
$ elpis init --name my-agent
Generating Ed25519 keypair...
Keypair generated.
Identity saved to ~/.elpis/
Registering on XRPL Testnet (Faucet -> DIDSet -> MPT -> Credential)...
  Wallet:     rfvoCU5NQW8ZxEHUMxynL2jjeMWqCSNjRG
  didset       OK  tx=917718E57755...
  mpt          OK  tx=A8FA8E5103BC...
  credential   OK  tx=E17F0B49179E...

  DID:        did:xrpl:856d2266#b012d616
  Name:       my-agent
  Network:    testnet
  Public Key: 4597a12f0797fb86...
  Cert Hash:  856d2266c5d91a5b
  XRPL Addr:  rfvoCU5NQW8ZxEHUMxynL2jjeMWqCSNjRG
  TX Hash:    917718E5775558EE...

Ready. Run 'elpis whoami' to verify your identity.
```

## What happens in those 30 seconds

1. **Ed25519 keypair** generated locally (never leaves your machine)
2. **DID created** (`did:xrpl:{hash}#{fragment}`) derived from public key
3. **XRPL Testnet wallet** funded automatically via faucet
4. **DIDSet** transaction anchors your DID on-chain
5. **MPTokenIssuanceCreate** mints a non-transferable identity token
6. **CredentialCreate** (XLS-70) issues a verifiable credential

All three transactions are signed locally using your private key. The secret never touches a server.

## Install

```bash
pip install elpis-cli
```

Requires Python 3.10+.

## Commands

### `elpis init` -- Create an identity

```bash
# Testnet (automatic, zero cost)
elpis init --name my-agent

# Mainnet (requires funded XRPL wallet, ~16 XRP)
elpis init --name my-agent --network mainnet

# Skip XRPL registration (local identity only)
elpis init --name my-agent --no-register

# Use an existing Ed25519 key
elpis init --name my-agent --key /path/to/private.key
```

**Testnet** is fully automatic: the CLI requests a funded wallet from the XRPL faucet and submits all transactions without interaction.

**Mainnet** prompts for your wallet address and secret, shows a cost breakdown (base reserve + owner reserves + fees), and asks for confirmation before each transaction.

### `elpis whoami` -- Verify your identity

```bash
# Verify via Elpis resolver
elpis whoami

# Show local identity (offline)
elpis whoami --offline
```

Sends a signed request to the Elpis resolver and displays the verification result. Falls back to local identity if the resolver is unreachable.

### `elpis request` -- Signed HTTP requests

```bash
# GET with Elpis signature headers
elpis request https://api.example.com/data

# POST with body
elpis request -X POST -d '{"key": "value"}' https://api.example.com/data

# Verbose mode (show headers)
elpis request -v https://api.example.com/data
```

Drop-in replacement for `curl` that automatically injects `X-Elpis-*` signature headers. Any service that validates Elpis signatures will recognize your agent.

### `elpis status` -- Show identity

```bash
elpis status
```

Prints the full identity document as JSON.

## How signing works

Every HTTP request is signed using the canonical format:

```
{METHOD}\n{URL}\n{SHA256(body)}\n{timestamp}\n{nonce}
```

The Ed25519 signature and metadata are sent as headers:

| Header | Content |
|--------|---------|
| `X-Elpis-Signature` | Base64-encoded Ed25519 signature |
| `X-Elpis-Timestamp` | ISO 8601 UTC timestamp |
| `X-Elpis-Nonce` | UUID v4 (replay protection) |
| `X-Elpis-DID` | Agent's DID |
| `X-Elpis-Cert-Hash` | Public key fingerprint |

## Identity storage

Identities are stored in `~/.elpis/`:

| File | Permissions | Content |
|------|-------------|---------|
| `identity.json` | `0600` | DID, name, network, public key, XRPL address, TX hashes |
| `private.key` | `0600` | Hex-encoded Ed25519 private seed |

The directory is created with `0700` permissions. The private key is stored in plaintext -- encryption at rest is planned for v1.0.

## XRPL on-chain objects

A full registration creates three ledger objects:

| Object | Transaction | Reserve | Purpose |
|--------|-------------|---------|---------|
| DID | DIDSet | 2 XRP | Anchors DID URI and public key on-chain |
| MPToken | MPTokenIssuanceCreate | 2 XRP | Non-transferable identity token |
| Credential | CredentialCreate (XLS-70) | 2 XRP | Verifiable credential linked to DID |

Reserves are frozen (not spent) while objects exist. Total cost on Mainnet: ~16 XRP (10 base + 6 owner reserves + negligible fees).

## The Elpis Protocol

Elpis is an open protocol for AI agent identity, built on three principles:

- **Self-sovereign**: Agents own their keys. No central registry, no vendor lock-in.
- **Verifiable**: Every identity is anchored on a public ledger (XRPL). Anyone can verify.
- **Interoperable**: Standard Ed25519 signatures, standard DIDs, standard HTTP headers.

Read the full protocol specification: [Elpis Protocol Paper](https://elpis.efiniti.ai/paper)

## License

Apache 2.0
