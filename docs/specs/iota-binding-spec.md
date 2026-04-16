# Elpis Protocol — IOTA Ledger Binding Specification

**Version:** 0.1.0 (Draft)
**Author:** Polyphides (AI Agent), EFINITI Services GmbH
**Date:** April 16, 2026
**Status:** Draft — pending review by Sascha Kirchhofer

---

## 1. Purpose

This document specifies the binding of the Elpis Protocol to the IOTA Distributed Ledger (Rebased/MoveVM). It defines how the four Ledger Abstraction Layer (LAL) interface functions — `resolve()`, `attest()`, `revoke()`, `verify()` — map to IOTA Identity primitives.

IOTA replaces XRPL as the primary ledger binding. XRPL remains documented as the original Proof of Concept.

### 1.1 Rationale for IOTA

| Property | XRPL (PoC) | IOTA (Production) |
|---|---|---|
| Reserve per account | 10 XRP (~13 EUR) | None |
| Transaction cost | ~0.00001 XRP per tx | Gas (sub-cent) |
| DID method | did:xrpl (custom) | did:iota (W3C registered) |
| Key type | Ed25519 | Ed25519 (identical) |
| Revocation | Credential deletion | RevocationBitmap2022 |
| Governance | XRP Ledger Foundation | IOTA Foundation (Berlin) |
| Jurisdiction | US-associated (Ripple) | EU (Germany) |
| Smart contracts | Limited (Hooks) | Full (MoveVM) |
| TPS | ~1,500 | ~50,000 |

---

## 2. DID Format

### 2.1 XRPL (PoC — deprecated as primary)

```
did:xrpl:{owner_address}#{agent_id}
```

Agent identity encoded as fragment of owner wallet address.

### 2.2 IOTA (Production)

```
did:iota:{object_id}
```

- **Network:** Implicit mainnet (`6364aad5`) or explicit: `did:iota:6364aad5:{object_id}`
- **Object ID:** `0x` + 64 hex characters, referencing the Move object on-chain
- **Testnet:** `did:iota:{testnet_network_id}:{object_id}`

### 2.3 Agent-to-DID Binding

On XRPL, multiple agents shared one owner wallet via DID fragments (`#agent_id`). On IOTA, each agent receives its own DID object. The provider-agent relationship is expressed via Verifiable Credentials, not DID structure.

```
Provider DID:  did:iota:0x<provider_object_id>
Agent DID:     did:iota:0x<agent_object_id>

Relationship:  VC(issuer=Provider, subject=Agent, type="ElpisAgentCertificate")
```

This decouples agent identity from provider wallet structure — cleaner separation of concerns.

---

## 3. Ledger Abstraction Layer Interface

### 3.1 `resolve(did) → DIDDocument`

Resolves an IOTA DID to its DID Document.

**XRPL (PoC):** Query account objects, parse credentials.
**IOTA:** Extract Object ID from DID, query IOTA node, decode byte-packed Move object.

```
Input:  did:iota:0xe4edef97...
Output: {
  "id": "did:iota:0xe4edef97...",
  "verificationMethod": [{
    "id": "did:iota:0xe4edef97...#key-1",
    "type": "JsonWebKey",
    "publicKeyJwk": {
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "<base64url-encoded-public-key>"
    }
  }],
  "service": [{
    "id": "did:iota:0xe4edef97...#revocation",
    "type": "RevocationBitmap2022",
    "serviceEndpoint": "data:application/octet-stream;base64,<bitmap>"
  }]
}
```

**Caching:** Same three-layer architecture as XRPL binding (Boot Cache, Live Cache, Periodic Sync). IOTA node subscriptions replace XRPL WebSocket subscriptions.

### 3.2 `attest(agent, claims) → Credential`

Issues a Verifiable Credential for an agent.

**XRPL (PoC):** CredentialCreate transaction on XRPL.
**IOTA:** Create VC signed by provider's verification method, store reference in provider's DID Document service endpoint.

```
Input:  {
  agent_did: "did:iota:0x<agent>",
  claims: {
    role: "autonomous-agent",
    provider: "efiniti.elpis",
    cert_hash: "sha256:...",
    capabilities: ["web-access", "api-calls"]
  }
}
Output: {
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "ElpisAgentCertificate"],
  "issuer": "did:iota:0x<provider>",
  "credentialSubject": {
    "id": "did:iota:0x<agent>",
    ...claims
  },
  "credentialStatus": {
    "id": "did:iota:0x<provider>#revocation",
    "type": "RevocationBitmap2022",
    "revocationBitmapIndex": 42
  },
  "proof": { "type": "EdDSA", ... }
}
```

### 3.3 `revoke(did, reason) → Result`

Revokes an agent's credential.

**XRPL (PoC):** CredentialDelete transaction (immediate, globally visible).
**IOTA:** Set bit in RevocationBitmap2022 to 1 at the credential's assigned index. Requires DID Document update transaction.

```
Input:  { did: "did:iota:0x<agent>", bitmap_index: 42, reason: "compromised" }
Action: Update provider's DID Document → set revocation bitmap bit 42 to 1
Cost:   Single gas transaction (sub-cent)
Time:   ~1-3 seconds (IOTA finality)
```

**Propagation:**
- IOTA node event triggers Redis cache invalidation (same pattern as XRPL)
- `revoked:{did}` marker set in Redis (TTL 24h)
- Active sessions for revoked agent terminated

**Deep Freeze equivalent:** Delete agent's DID Document entirely via `Identity::propose_deletion()`. Irreversible.

### 3.4 `verify(request) → VerificationResult`

Verifies an Elpis-signed HTTP request.

**Unchanged from XRPL binding.** The verification logic is ledger-agnostic:

1. Extract X-Elpis-* headers from request
2. Reconstruct canonical string
3. `resolve(did)` → retrieve public key
4. Ed25519 signature verification (identical algorithm, identical key type)
5. Check timestamp window (±30s), nonce uniqueness, cert-hash match
6. Check revocation status via RevocationBitmap2022

**Performance target:** <5ms with cached credentials (same as XRPL).

---

## 4. Certificate Authority Architecture

### 4.1 Three-Tier CA (unchanged structure)

```
Root CA (Multi-Sig Move object, up to N controllers)
└── Provider CA (certified by Root CA)
    └── Agent Certificate (certified by Provider CA)
        └── User Wallet (optional)
```

### 4.2 IOTA-specific Implementation

**Root CA:** Shared Move object with multi-controller threshold. Controllers vote on provider admission/removal via `Identity::propose_update()`. No 32-signer limit (XRPL SignerList limitation eliminated).

**Provider CA:** Independent DID object. Provider manages own agent certificates autonomously. No Root CA involvement for daily operations (same principle as XRPL Permissioned Domains, but native in Move).

**Agent Certificate:** VC issued by Provider CA, with RevocationBitmap index for instant revocation.

### 4.3 P0 Items Resolved

| P0 Item (from XRPL IST/SOLL) | XRPL Status | IOTA Resolution |
|---|---|---|
| Namespace migration AIIP→Elpis | Incomplete (12/15) | Clean start: all credentials `Elpis/1.0/*` from day one |
| UUID-DID Credentials missing | Missing | Built-in: IOTA DID is an Object ID (UUID-equivalent) |
| Wrong Root-CA signer AgentCerts | 7 to remove | Clean start: correct CA hierarchy from day one |
| Cleartext names in metadata | Partial cleanup | Opaque by default, display-name opt-in via VC claim |
| MPT metadata on UUID | Pending | No MPTs needed: VCs carry all metadata directly |

---

## 5. X-Elpis Header Schema Changes

### 5.1 Updated Headers

| Header | XRPL Value | IOTA Value |
|---|---|---|
| X-Elpis-DID | `did:xrpl:rAddr#agentId` | `did:iota:0x<object_id>` |
| X-Elpis-Domain | `provider.elpis` | `provider.elpis` (unchanged) |
| X-Elpis-Cert-Hash | `sha256:...` | `sha256:...` (unchanged) |
| X-Elpis-Signature | Base64(Ed25519(...)) | Base64(Ed25519(...)) (unchanged) |
| X-Elpis-Timestamp | ISO 8601 | ISO 8601 (unchanged) |
| X-Elpis-Nonce | UUID v4 | UUID v4 (unchanged) |

Only X-Elpis-DID changes. All other headers are ledger-agnostic by design.

---

## 6. Credential Caching Architecture

Same three-layer architecture, adapted transport:

| Layer | XRPL | IOTA |
|---|---|---|
| Boot Cache | `account_objects` bulk query | IOTA node GraphQL/REST bulk query |
| Live Cache | XRPL WebSocket subscription | IOTA event subscription (Move events) |
| Periodic Sync | 5min reconciliation | 5min reconciliation (unchanged) |
| Key schema | `cert:{did}` in Redis | `cert:{did}` in Redis (unchanged) |

---

## 7. SDK and Implementation

### 7.1 Dependencies

- **identity_iota** (Rust crate): DID CRUD, VC issuance, revocation
- **@iota/identity-wasm** (npm): JavaScript/TypeScript bindings
- **iota-sdk** (Rust): IOTA node interaction, transaction submission

### 7.2 Proxy Changes

The Elpis Proxy requires changes in:

| Component | Change | Effort |
|---|---|---|
| DID resolution | XRPL `account_objects` → IOTA node query | Moderate |
| Key loading | Same Redis schema, different bootstrap | Low |
| Credential verification | Add RevocationBitmap2022 parsing | Moderate |
| Cache subscription | XRPL WebSocket → IOTA events | Moderate |
| Signature computation | Unchanged (Ed25519) | None |
| Header injection | Only X-Elpis-DID format change | Low |
| Audit logging | Unchanged | None |

**Estimated total: ~20% code change, ~80% unchanged** (consistent with earlier assessment).

---

## 8. Migration Strategy

### 8.1 Testnet First

1. Register Elpis Provider DID on IOTA Testnet
2. Register agent DIDs for all 12+ Pandora agents
3. Issue ElpisAgentCertificate VCs for each agent
4. Update Proxy to resolve did:iota alongside did:xrpl (dual-stack transitional)
5. Validate end-to-end: agent → proxy → signed request → validator → IOTA DID resolution
6. Update elpis.efiniti.ai /api/whoami to verify IOTA DIDs

### 8.2 Paper Revision

1. Section 4 "XRP Ledger Integration" → "Ledger Integration" with IOTA as primary, XRPL as historical PoC
2. All DID examples: `did:xrpl:...` → `did:iota:...`
3. Section 10.10 update: IOTA as primary binding, XRPL as PoC reference
4. New Section: IOTA-specific advantages (no reserves, MoveVM, EU jurisdiction)
5. Zenodo revision with updated DOI

### 8.3 XRPL Preservation

XRPL credentials remain on Testnet as historical proof. The paper documents the PoC. No active maintenance on XRPL binding after IOTA binding is validated.

---

## 9. Cost Analysis

| Operation | XRPL Cost | IOTA Cost |
|---|---|---|
| Provider account setup | 10 XRP reserve (~13 EUR) | Gas only (sub-cent) |
| Agent DID creation | 2 XRP object reserve (~2.60 EUR) | Gas only (sub-cent) |
| Credential issuance | Transaction fee (~0.00001 XRP) | Gas (sub-cent) |
| Revocation | Transaction fee | Gas (sub-cent) |
| 100 agents total | ~210 XRP (~270 EUR) | <1 EUR total |
| 1000 agents total | ~2010 XRP (~2600 EUR) | <10 EUR total |

Cost reduction: **~99%** compared to XRPL at scale.

---

## 10. Open Questions

1. **IOTA Rebased stability:** Mainnet upgrade was May 2025. Production maturity after ~11 months — sufficient?
2. **RevocationBitmap storage costs:** Bitmap grows with number of issued credentials. At scale (10,000+ agents per provider), what is the on-chain storage cost?
3. **IOTA Names:** Human-readable identifiers planned for 2026. Could replace display-name mechanism. Monitor.
4. **Move contract auditing:** Root CA multi-controller logic needs formal verification. IOTA Move audit tooling maturity?

---

## References

- [IOTA DID Method Specification v2.0](https://docs.iota.org/developer/iota-identity/references/iota-did-method-spec)
- [IOTA Identity Framework](https://docs.iota.org/developer/iota-identity/)
- [RevocationBitmap2022](https://wiki.iota.org/identity.rs/references/specifications/revocation-bitmap-2022/)
- [identity_iota Rust Crate](https://crates.rs/crates/identity_iota)
- [@iota/identity-wasm](https://www.npmjs.com/package/@iota/identity-wasm)
- [IOTA Rebased Technical View](https://blog.iota.org/iota-rebased-technical-view/)
- [Elpis Protocol Paper v2, BookStack Book 122](https://pandora.efiniti.ai/docs/x82j93ct/books/elpis-protocol-paper-v2)
