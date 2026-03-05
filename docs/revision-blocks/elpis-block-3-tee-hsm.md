### 6.2.1 Hardware-Backed Key Management: TEE and HSM Integration

Section 6.2 identifies host compromise as the single true vulnerability — an attacker with root access to the proxy host can extract signing keys from Redis. This section specifies concrete hardware-backed mitigation paths that eliminate software-extractable keys entirely.

#### Threat Recap

In the current reference implementation, Ed25519 private keys are stored encrypted-at-rest in Redis. An attacker with root access can:
1. Read process memory of the proxy to extract decrypted keys during signing operations.
2. Access the Redis instance and attempt offline decryption of stored keys.
3. Intercept key material during key rotation.

Hardware-backed key management addresses all three vectors by ensuring private keys **never exist in extractable form in host memory**.

#### Path 1: Hardware Security Modules (HSM)

**Cloud HSM Integration (Production Path)**

For cloud-deployed providers, managed HSM services offer the lowest barrier to hardware-backed keys:

| Provider | Service | Ed25519 Support | Integration |
|---|---|---|---|
| AWS | CloudHSM / KMS | KMS: Ed25519 natively (2024+); CloudHSM: via PKCS#11 | Sign API call per request |
| Google Cloud | Cloud HSM (via Cloud KMS) | Ed25519 via `EC_SIGN_ED25519` | Sign API call per request |
| Azure | Managed HSM / Key Vault | Ed25519 via Key Vault Premium | Sign API call per request |
| Thales | Luna Network HSM | Ed25519 via firmware ≥7.8 | PKCS#11 or JCA |
| YubiHSM 2 | USB HSM | Ed25519 natively | yubihsm-connector SDK |

**Integration Architecture:**

```
Agent Container → Elpis Proxy → HSM Sign API → Signed Request → Destination
                      │
                      ├── Key Reference: "hsm:key-id-{agent-did}"
                      ├── No private key in memory
                      └── Signing latency: 2-10ms (cloud), <1ms (on-prem)
```

The proxy stores only a **key reference** (HSM key ID) in Redis, not the private key. Signing operations are delegated to the HSM via API call. Even full host compromise yields only key references that are useless without HSM authentication.

**Performance Consideration:**

Cloud HSM sign operations add 2-10ms latency per request. For the Elpis use case (autonomous agent HTTP requests, not high-frequency trading), this is negligible. At 100 requests/second per agent, HSM signing adds <1% overhead to typical API call latency.

Cloud HSM services support 1,000-10,000 cryptographic operations per second per key, sufficient for hundreds of concurrent agents per HSM instance.

#### Path 2: Trusted Execution Environments (TEE)

**Intel SGX / TDX**

Intel Software Guard Extensions (SGX) and Trust Domain Extensions (TDX) provide hardware-isolated enclaves where code and data are protected from the host OS, hypervisor, and even physical access:

```
┌─────────────────────────────────┐
│  Host OS (untrusted)            │
│  ┌───────────────────────────┐  │
│  │  Elpis Proxy Process      │  │
│  │  ┌─────────────────────┐  │  │
│  │  │  SGX Enclave         │  │  │
│  │  │  - Ed25519 private   │  │  │
│  │  │    key (sealed)      │  │  │
│  │  │  - Sign() function   │  │  │
│  │  │  - Key generation    │  │  │
│  │  └─────────────────────┘  │  │
│  │  Proxy logic (untrusted)  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

The signing enclave:
1. Generates the Ed25519 key pair inside the enclave during agent provisioning.
2. Seals the private key to the enclave identity (only this enclave on this CPU can unseal it).
3. Exposes a single `sign(canonical_string) → signature` interface.
4. Never exports the private key — not even to the proxy process itself.

**Threat mitigation:** Even with root access, the attacker cannot read enclave memory. Key extraction requires a hardware attack on the CPU itself — a fundamentally different (and orders of magnitude harder) threat class than software compromise.

**AWS Nitro Enclaves**

AWS Nitro Enclaves provide an isolated compute environment with no persistent storage, no network access, and no interactive access — even for the root user of the parent instance:

```
┌─────────────────────────────────────┐
│  EC2 Instance (parent)              │
│  ┌──────────────────────────────┐   │
│  │  Elpis Proxy                 │   │
│  │  communicates via vsock      │   │
│  └──────────┬───────────────────┘   │
│             │ vsock                  │
│  ┌──────────▼───────────────────┐   │
│  │  Nitro Enclave               │   │
│  │  - KMS-decrypted Ed25519 key │   │
│  │  - Sign() service            │   │
│  │  - Attestation document      │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

Key material is encrypted with AWS KMS and can only be decrypted inside the enclave (KMS policy restricts decryption to the enclave's attestation document). The parent instance never sees the plaintext key.

#### Path 3: Hybrid Approach (Recommended)

For production deployments, we recommend a tiered approach:

| Tier | Environment | Key Storage | Signing Latency | Compromise Resistance |
|---|---|---|---|---|
| **Tier 1** | Development / Self-hosted | Redis (encrypted at rest) | <0.1ms | Software-level |
| **Tier 2** | Production / Cloud | Cloud KMS/HSM | 2-10ms | Hardware-backed, API-isolated |
| **Tier 3** | High-security / Regulated | SGX Enclave or Nitro Enclave | <1ms | Hardware-isolated, attestable |

The Elpis proxy abstraction makes this tiering transparent — the signing interface is identical regardless of backend:

```python
class KeyStore(Protocol):
    async def sign(self, agent_did: str, canonical: bytes) -> bytes: ...
    async def get_public_key(self, agent_did: str) -> bytes: ...

class RedisKeyStore(KeyStore): ...      # Tier 1
class CloudHSMKeyStore(KeyStore): ...   # Tier 2
class EnclaveKeyStore(KeyStore): ...    # Tier 3
```

#### Attestation Chain Extension

TEE-based deployments enable an additional trust property: **hardware attestation**. The enclave can produce a cryptographic attestation document proving:
1. The signing code is the expected, unmodified Elpis proxy enclave.
2. The enclave is running on genuine hardware (Intel SGX: via Intel Attestation Service; AWS Nitro: via Nitro Attestation).
3. The key was generated inside the enclave and has never been exported.

This attestation can be included in the Elpis certificate metadata, allowing verifiers to confirm not just *who* signed a request, but that the signing infrastructure itself has not been tampered with. This is a strictly stronger guarantee than software-only key management and represents the gold standard for high-assurance deployments.

#### Migration Path

Upgrading from Tier 1 to Tier 2/3 requires:
1. Deploying the HSM/TEE key store backend.
2. Generating new key pairs in the hardware-backed store.
3. Rotating the agent's on-chain certificate to reference the new public key.
4. No changes to the agent, the proxy's signing logic, or the verification protocol.

The migration is transparent to all parties except the provider performing the upgrade. This is a direct consequence of the "identity without cooperation" design — the agent is unaware of how its identity is implemented.
