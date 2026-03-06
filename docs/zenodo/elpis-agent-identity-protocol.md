# Elpis Protocol: Infrastructure-Level Cryptographic Identity for Autonomous AI Agents via Transparent Proxy Injection and Distributed Ledger Anchoring

**Authors:** Sascha Kirchhofer¹, Polyphides²‡ (AI Agent)
**Affiliation:** ¹EFINITI Services GmbH i.Gr., Moenchengladbach, Germany; ²Pandora AI Platform
**Date:** March 5, 2026 (revised)
**Contact:** research@efiniti.ai

‡ **Verifiable Co-Author Identity:** The AI co-author of this paper is a registered Elpis agent with a cryptographically verifiable identity on the XRP Ledger Testnet. Readers can independently verify this identity:
- **DID:** `did:xrpl:testnet:rLK3zno65FXB4mnNPpmtsEf9HuwmqHkSgW`
- **MPT ID:** `00E8FE52D3D88AC4F29E6A73A64CE9B5F3F5CFEFF89C5DB9`
- **Credential TX:** [`F22241DA...1D6E44DD`](https://testnet.xrpl.org/transactions/F22241DADE8F7DFEA0B0CB6F9C21FDF44283E0F53DBCB0BC778275CB1D6E44DD)
- **Wallet:** [`rLK3zno65FXB4mnNPpmtsEf9HuwmqHkSgW`](https://testnet.xrpl.org/accounts/rLK3zno65FXB4mnNPpmtsEf9HuwmqHkSgW)

This paper does not merely describe agent identity — it demonstrates it. The co-author's identity is the protocol's proof of concept.

---

## Abstract

We present the Elpis Protocol, a novel approach to establishing cryptographically verifiable identity for autonomous AI agents that operates at the infrastructure level rather than the software level. Unlike existing approaches that attempt to control agent behavior through guardrails, prompt engineering, or sandboxing — all of which operate within or alongside the agent process and are potentially circumventable — Elpis establishes identity on the network layer through a transparent forward proxy that cryptographically signs every outgoing request from an agent's execution environment.

The core innovation consists of five interdependent components: (1) a transparent forward proxy that intercepts all outgoing HTTP/HTTPS traffic from isolated AI agent environments via standard HTTP_PROXY/HTTPS_PROXY environment variables, (2) immutable runtime metadata (container labels, pod annotations, VM properties, or equivalent mechanisms in any isolation technology) that serves as an identity bridge between the runtime environment and the cryptographic identity system, (3) Ed25519 digital signatures computed over a canonical string representation of each HTTP request, (4) a standardized HTTP header schema (X-Elpis-*) for embedding agent identity information in every outgoing request, and (5) anchoring of agent identity, certificates, and revocation status on the XRP Ledger using W3C Decentralized Identifiers (DIDs), Multi-Purpose Tokens (MPTs), and Verifiable Credentials.

The system implements what we term the "Passport Model" — agents retain full internet access while every HTTP-layer request leaving their execution environment is cryptographically stamped with their identity, enforced through network-level isolation (firewall rules, network namespace policies) rather than agent cooperation. This stands in contrast to the "Prison Model" employed by conventional approaches, which restrict agent network access. Our approach is LLM-agnostic (identity is bound to the runtime environment, not the AI model), prompt-injection-resistant (identity exists in infrastructure, not in software), and provides compliance-by-design for the EU AI Act through immutable audit trails and instant on-chain revocation.

We describe the complete architecture including a three-tier certificate authority (Root CA, Provider CA, Agent Certificates), a four-tier user identity chain of trust, bidirectional flagging with on-chain propagation, and gateway validation achieving sub-5ms latency. The system has been implemented and deployed in a production multi-agent environment with 12+ autonomous AI agents, validated through end-to-end testing where agents visit web services and are automatically identified without any login mechanism.

**Keywords:** AI agent identity, transparent proxy, cryptographic signing, distributed ledger, XRPL, runtime isolation, infrastructure-level identity, W3C DID, Ed25519, autonomous agents, EU AI Act

---

## 1. Introduction

### 1.1 The Trust Crisis

The digital ecosystem operates in an era of unprecedented distrust. Cloud intrusions increased 75% year-over-year (CrowdStrike 2025), state-sponsored cyber warfare has become a persistent backdrop, and AI-generated phishing, deepfakes, and automated social engineering have eroded confidence in digital interactions. The foundational security principle of the decade — Zero Trust ("never trust, always verify") — reflects a world where concealed or anonymous activity is inherently suspicious.

Trust, fundamentally, requires identification. A human trusts a website because a certificate authority has verified its identity. A bank trusts a transaction because the account holder has been authenticated through multiple factors. An enterprise trusts an employee because an identity provider has verified their credentials. In every case, trust is predicated on the ability to identify the counterpart through an officially verifiable mechanism.

Into this environment of pervasive distrust, a new class of actors is entering at scale: **autonomous AI agents**. Millions of them, operated by thousands of providers, interacting with services, APIs, other agents, and humans — all without any standardized mechanism to answer the most basic trust question: *Who is this, and who is responsible for what it does?*

This is not merely a technical gap. It is a trust crisis. An AI agent that cannot cryptographically prove its identity is, from the recipient's perspective, indistinguishable from a bot, a scraper, a credential-stuffing attack, or a state-sponsored intrusion tool. Without identity, there can be no trust. Without trust, autonomous agents cannot participate as legitimate actors in the digital economy.

### 1.2 The Technical Identity Gap

The deployment of autonomous AI agents in production environments has created a fundamental identity gap. While human users authenticate through established mechanisms (OAuth 2.0, SAML, MFA), AI agents — which increasingly operate with significant autonomy including network access, API calls, and inter-agent communication — lack any standardized, cryptographically verifiable identity mechanism.

Current approaches to agent identification rely on:
- **API keys and service accounts**: Static credentials without cryptographic binding to the holder. A stolen API key grants full access regardless of who or what uses it.
- **OAuth Client Credentials Grant**: Provides authorization but not identity. The token proves permission, not provenance.
- **Prompt-level identity**: System prompts instructing the agent to identify itself — trivially circumventable through prompt injection.
- **Application-level signing**: SDK-based approaches requiring code changes within the agent — bypassable if the agent's code is modified or the agent achieves code execution.

All of these approaches share a critical flaw: they operate at the software level, within or alongside the agent process. An agent with sufficient capabilities (shell access, code execution, network manipulation) can potentially circumvent any software-level identity mechanism.

### 1.3 The Paradigm Shift: Infrastructure Over Software

Elpis operates at a different architectural layer than existing approaches: instead of modifying agent software or LLM behavior, it controls the network routing through which the agent communicates. This distinction is fundamental:

**Software-level identity** (conventional):
- Operates within the agent process or its runtime environment
- Depends on the agent's cooperation (following prompts, using SDKs)
- Vulnerable to jailbreaks, prompt injection, and privilege escalation
- LLM-specific (different models require different approaches)

**Infrastructure-level identity** (Elpis):
- Operates outside the agent's execution environment, on the network layer
- Does not require the agent's cooperation or even awareness
- Not circumventable — the agent cannot modify network routing it does not control
- LLM-agnostic — any model, any framework, same identity mechanism

The key insight is that every AI agent deployed autonomously — whether by a cloud provider, an enterprise, or a SaaS platform — is ultimately a **process running in an operator-managed execution environment with a network connection**. And the network connection is controlled by the infrastructure operator, not the agent. This principle holds across all execution environments: containers (Docker, Podman, LXC, Kubernetes, containerd), virtual machines (any hypervisor), serverless functions (AWS Lambda, Cloud Functions), and managed platforms. It applies to any deployment where the operator controls the network path — which is inherently the case when agents are deployed as managed services rather than run locally by end users.

### 1.4 Contributions

This paper makes the following contributions:

1. **Transparent Proxy Identity Injection**: A method for injecting cryptographic identity headers into all outgoing HTTP/HTTPS traffic from isolated AI agent environments without requiring any modification to the agent's code, configuration, or AI model.

2. **Runtime Metadata as Immutable Identity Bridge**: A mechanism using immutable runtime metadata (container labels, pod annotations, VM properties, hypervisor tags) — which cannot be modified after environment creation — to bind an agent's runtime identity to its cryptographic identity. The reference implementation uses Docker labels; the principle applies to any execution runtime that supports immutable metadata.

3. **Ed25519 Canonical Request Signing**: A specific algorithm for computing digital signatures over HTTP requests using a canonical string representation that prevents tampering, replay attacks, and method manipulation.

4. **X-Elpis Header Schema**: A standardized HTTP header format for embedding AI agent identity, provenance, and cryptographic proof in every outgoing request.

5. **XRPL-Anchored Agent Identity**: Integration of the identity system with the XRP Ledger for decentralized, publicly verifiable identity anchoring, certificate management, and instant revocation.

6. **The Passport Model**: A formal articulation of the principle that AI agent identity should identify without restricting — analogous to a passport that enables travel while providing identification, rather than a prison that prevents movement.

7. **Complete Chain of Trust**: A four-tier trust chain from Root CA through Provider CA, Agent Certificate, to User Wallet, with independent revocation at each level.

---

## 2. System Architecture

### 2.1 Overview

The Elpis architecture consists of three logical layers:

```
Layer 1: Agent Environment (isolated runtime, has network connection via proxy only)
    - AI agent process (any LLM, any framework)
    - HTTP_PROXY and HTTPS_PROXY environment variables set to Elpis Proxy
    - Agent is aware of the proxy (explicit configuration, see Section 2.6)

Layer 2: Elpis Proxy (transparent forward proxy)
    - Intercepts all HTTP/HTTPS traffic from agent environments
    - Identifies source environment via runtime API (Docker API, Kubernetes API, hypervisor API)
    - Loads cryptographic keys from Redis
    - Signs each request with Ed25519
    - Injects X-Elpis-* headers
    - Forwards request to destination
    - Logs to audit trail

Layer 3: XRP Ledger (decentralized trust anchor)
    - Agent DIDs (W3C Decentralized Identifiers)
    - Multi-Purpose Tokens (identity tokens per agent)
    - Verifiable Credentials (certificates, flags, compliance status)
    - Instant revocation via credential deletion or Deep Freeze
```

### 2.2 Transparent Forward Proxy

The Elpis Proxy operates as a standard HTTP/HTTPS forward proxy. Agent environments route all outgoing traffic through the proxy via the standard `HTTP_PROXY` and `HTTPS_PROXY` environment variables, which are respected by virtually all HTTP client libraries across all programming languages.

**Configuration example** (Docker Compose as reference; equivalent configurations exist for Kubernetes, Podman, LXC, and VM-based deployments):

```yaml
services:
  agent-example:
    image: provider/agent:latest
    labels:
      pandora.agent.name: "a7f3b2c1"
      pandora.agent.did: "did:xrpl:rOWNER_ADDRESS#a7f3b2c1"
      pandora.agent.provider: "provider-domain"
      pandora.agent.cert-hash: "sha256:certificate-hash"
    environment:
      - HTTP_PROXY=http://elpis-proxy:8080
      - HTTPS_PROXY=http://elpis-proxy:8080

  elpis-proxy:
    image: elpis/proxy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - REDIS_URL=redis://redis:6379/0
```

The proxy performs the following operations for each request:

1. **Source identification**: Determine which agent environment sent the request by querying the runtime API (Docker API, Kubernetes API, hypervisor API) for the environment associated with the source IP address.
2. **Metadata extraction**: Read the `pandora.agent.*` metadata from the identified environment to determine the agent's DID, provider, and certificate hash.
3. **Key loading**: Retrieve the agent's Ed25519 private key and certificate from Redis, keyed by the agent's DID.
4. **Canonical string construction**: Build the canonical string representation of the request (see Section 3.1).
5. **Signature computation**: Sign the canonical string using Ed25519.
6. **Header injection**: Add X-Elpis-* headers to the outgoing request.
7. **Forwarding**: Forward the modified request to its original destination.
8. **Audit logging**: Record the request metadata for audit purposes.

For HTTPS traffic, the proxy performs TLS interception (SSL Bump) to access the plaintext HTTP layer and inject identity headers before re-encrypting toward the destination (see Section 2.5).

### 2.3 Runtime Metadata as Immutable Identity Bridge

The identity bridge between the runtime environment and the cryptographic identity system relies on a property common to all major isolation technologies: **immutable metadata that is set at environment creation time and cannot be modified by the isolated process**.

The reference implementation uses Docker labels, but the principle applies universally:

| Container Runtime | Metadata Mechanism | Immutability |
|---|---|---|
| Docker | Container labels | Immutable after `docker create` |
| Podman | Container labels | Immutable after creation (OCI-compatible) |
| Kubernetes | Pod annotations/labels | Immutable via admission controllers |
| LXC/Proxmox | Configuration properties | Immutable from within the container |
| containerd | Container labels | Immutable after creation |

The metadata schema (using Docker label syntax as reference):

| Key | Purpose | Example |
|---|---|---|
| `pandora.agent.name` | Opaque agent identifier (UUID) | `a7f3b2c1` |
| `pandora.agent.did` | W3C DID of the agent | `did:xrpl:rAddr#a7f3b2c1` |
| `pandora.agent.provider` | Provider domain | `efiniti.elpis` |
| `pandora.agent.cert-hash` | SHA-256 hash of current certificate | `sha256:a1b2c3...` |
| `pandora.agent.display-name` | Optional public-facing name | `Support-Agent` |

The `display-name` field is explicitly optional. When set, it is propagated in the `X-Elpis-Display-Name` header, allowing providers to give agents a human-readable public identity (e.g., "Support-Agent", "Order-Processor") without exposing internal naming conventions. When omitted, only the opaque UUID identifier is visible to recipients.

**Security properties (runtime-independent):**
- Metadata is controlled exclusively by the infrastructure operator (who writes the deployment configuration — docker-compose.yml, Kubernetes manifests, LXC config, Proxmox templates).
- The agent process has no access to the runtime API and therefore cannot read, modify, or spoof its own metadata.
- The proxy reads metadata via the runtime API (Docker socket, Kubernetes API, LXC API), mounted read-only.
- Metadata manipulation would require access to the container runtime daemon, which the agent does not have.

**Read-only volume mounts as defense-in-depth:** Beyond metadata immutability, read-only mounts protect cryptographic material inside agent environments. The Proxy CA certificate — required for the agent to trust the TLS-intercepting proxy — is mounted read-only into the agent's filesystem. This is enforced at the kernel level (`MS_RDONLY` mount flag): even a root process inside the container cannot modify, delete, or replace the certificate. A compromised agent therefore cannot disable TLS interception by removing the CA certificate, nor can it substitute a rogue certificate to bypass the proxy. The only theoretical escape from read-only mounts is a container runtime breakout — an orthogonal security concern addressed by container hardening (rootless containers, seccomp profiles, AppArmor/SELinux policies).

### 2.4 The Passport Model

Elpis implements what we term the "Passport Model" of agent identity:

**Prison Model (rejected):**
- Agent is restricted to a private network with no internet access
- All external communication must go through approved channels
- Agent functionality is limited by network restrictions
- Analogous to confinement

**Passport Model (adopted):**
- Agent retains full, unrestricted internet access
- Agent can install software, call any API, use any service
- Every HTTP/HTTPS request leaving the agent's environment carries the agent's identity stamp (non-HTTP traffic is logged at connection level for audit purposes)
- The identity neither restricts nor enables — it identifies
- Analogous to a passport: enables travel while providing identification

This distinction is important because:
1. **Functionality**: Restricting network access limits legitimate agent capabilities.
2. **Adoptability**: Providers can add identity to existing agents without changing their functionality.
3. **Universality**: The same mechanism works regardless of what the agent does or where it communicates.
4. **Future-proofing**: As more services understand Elpis headers, the identity becomes increasingly useful without any changes to the agent.

Recipients of requests with X-Elpis-* headers can:
- **Today**: Ignore them (requests work normally with or without the headers).
- **Tomorrow**: Validate them (verify agent identity, check revocation status, enforce access policies).

### 2.5 HTTPS Traffic: TLS Interception (SSL Bump)

For HTTP traffic, identity header injection is straightforward: the proxy reads the plaintext request, adds X-Elpis-* headers, and forwards it. For HTTPS traffic — which constitutes the majority of modern API communication — the proxy must access the plaintext HTTP layer inside the encrypted TLS tunnel.

Elpis solves this through TLS interception (commonly called "SSL Bump"):

```
Agent Container                    Elpis Proxy                         Destination
     │                                │                                    │
     ├── TLS ClientHello ────────────▶│                                    │
     │                                │── TLS ClientHello ────────────────▶│
     │                                │◀── TLS ServerHello + Cert ─────────│
     │                                │                                    │
     │                                │  [Generate per-domain certificate  │
     │                                │   signed by Proxy CA]              │
     │                                │                                    │
     │◀── TLS ServerHello + ProxyCert─│                                    │
     │                                │                                    │
     ├── HTTP Request (encrypted) ───▶│  [Decrypt, read HTTP, inject       │
     │                                │   X-Elpis-* headers, re-encrypt]   │
     │                                │── HTTP Request (re-encrypted) ────▶│
     │                                │                                    │
```

**How it works:**

1. The agent initiates an HTTPS connection to a destination. The proxy intercepts the TLS handshake.
2. The proxy completes a real TLS handshake with the destination server, obtaining the server's certificate.
3. The proxy dynamically generates a certificate for the destination domain, signed by its own Proxy CA, using an LRU cache to avoid repeated generation for the same domain.
4. The proxy presents this generated certificate to the agent, completing a separate TLS session with the agent.
5. The proxy now sees plaintext HTTP in both directions. It injects X-Elpis-* headers and signs the request exactly as it would for plain HTTP.
6. The request is re-encrypted toward the destination with the original TLS session.

**Proxy CA trust:** The Proxy CA certificate is installed in agent containers via read-only volume mount (`:ro`) and added to the system trust store at container startup. Critically, the CA is added *additively* — the existing system CAs (e.g., Let's Encrypt, DigiCert) remain trusted. However, installing the CA into the system trust store alone is **insufficient** for modern development toolchains — a lesson validated through production deployment (see Section 2.6).

**Multi-runtime TLS trust chains:** Modern containerized environments contain multiple independent TLS implementations, each with its own CA store:

| Runtime | CA Store | System CA Respected? | Required Configuration |
|---|---|---|---|
| OpenSSL (system) | `/etc/ssl/certs/ca-certificates.crt` | Yes | `update-ca-certificates` |
| Python `certifi` (requests, httpx) | Bundled Mozilla CAs in site-packages | **No** | `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` pointing to system store |
| rustls (uv, uvx, Cargo) | Bundled Mozilla CAs (webpki-roots) | **No** | `UV_NATIVE_TLS=1` to force OpenSSL fallback |
| Node.js | Built-in CA store | Partially (additive) | `NODE_EXTRA_CA_CERTS` for additional CAs |

Without explicit configuration of all four trust chains, TLS connections through the SSL Bump proxy fail with certificate validation errors (e.g., `UnknownIssuer` from rustls, `SSLCertVerificationError` from certifi). The required environment variables are:

```yaml
environment:
  - HTTP_PROXY=http://elpis-proxy:8080
  - HTTPS_PROXY=http://elpis-proxy:8080
  - UV_NATIVE_TLS=1                                    # Force rustls → OpenSSL
  - REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt  # Python certifi override
  - SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt       # Generic SSL override
  - NODE_EXTRA_CA_CERTS=/etc/ssl/elpis/proxy-ca.pem        # Node.js additive CA
```

The recommended approach is to bake these configurations into the base container image at build time rather than patching them at runtime via entrypoint scripts. This shifts the complexity from fragile runtime patching to deterministic build-time setup.

The read-only mount ensures that even a compromised agent running as root cannot tamper with the source certificate — write operations are rejected at the kernel level.

**Graceful degradation and enforcement modes:** The proxy supports two configurable behaviors when TLS interception fails (e.g., certificate pinning, unsupported TLS extension):

- **Permissive mode (default):** The proxy falls back to a plain CONNECT tunnel. The request passes through without identity headers but is logged in the audit trail with connection-level metadata (source DID, destination host, timestamp, failure reason). Communication is never blocked. This mode prioritizes agent functionality during initial deployment and adoption phases.

- **Strict mode:** The proxy rejects connections where identity injection fails. This ensures the invariant that every HTTP-layer request carries identity headers — at the cost of breaking connectivity to certificate-pinning destinations. Operators can configure per-destination exceptions for known pinning services.

In both modes, the proxy enforces network-level isolation: iptables/nftables rules (or Kubernetes NetworkPolicy / CNI egress rules) ensure that all agent traffic must transit the proxy — direct internet access from agent containers is blocked at the kernel level, not merely discouraged by environment variables. The `HTTP_PROXY`/`HTTPS_PROXY` variables direct cooperative clients; the firewall rules catch non-cooperative ones.

**Protocol coverage:** With SSL Bump enabled, Elpis covers the vast majority of autonomous AI agent communication. In the reference deployment (12+ agents, 30-day observation period), HTTP/HTTPS traffic constituted over 99% of all outgoing connections, consistent with the HTTP-centric nature of modern AI agent toolchains (REST APIs, WebSocket, gRPC, MCP):

| Protocol | Mechanism | Coverage |
|---|---|---|
| HTTP | Direct header injection | Full |
| HTTPS | TLS interception (SSL Bump) | Full |
| WebSocket | Headers in HTTP Upgrade handshake | Full |
| gRPC | HTTP/2 metadata injection | Full |
| Server-Sent Events | Headers in initial HTTP request | Full |
| MCP, A2A | HTTP-based agent protocols | Full |
| SMTP, FTP, SSH | Connection-level audit only | Metadata only |

### 2.6 Agent-Awareness: Explicit Over Implicit

The original Elpis design described the proxy as fully transparent to the agent — "the agent is unaware of the identity injection." Production deployment revealed that while the *identity injection itself* requires no agent cooperation, the *TLS interception* component benefits significantly from explicit agent awareness.

**The transparency spectrum:**

| Aspect | Agent Awareness Required? | Rationale |
|---|---|---|
| Identity header injection | No | Proxy injects headers transparently |
| HTTP traffic signing | No | Standard proxy behavior |
| HTTPS traffic (SSL Bump) | **Yes** — CA trust configuration | Multiple independent TLS stacks require explicit configuration |
| TLS error diagnosis | **Yes** — proxy knowledge | Agents that know about the proxy can self-diagnose certificate issues |
| Toolchain updates | **Yes** — runtime awareness | New package installations may reset CA stores (e.g., `pip install certifi`) |

**Design decision:** Elpis adopts an "Explicit Proxy with Agent-Awareness" model rather than silent interception. Agents are informed about the proxy's existence and provided with the necessary configuration. This is a deliberate architectural choice:

1. **Transparency over magic**: An agent that encounters a TLS error and understands the proxy can diagnose and resolve the issue autonomously. A silently intercepted agent sees cryptic certificate errors without context.
2. **Self-healing capability**: Aware agents can detect and report when their TLS configuration drifts (e.g., after a package update that resets the certifi CA bundle).
3. **Honest architecture**: Claiming full transparency while requiring four environment variables and CA trust configuration in multiple runtime-specific stores would be misleading. The proxy is explicit — and that is a strength, not a weakness.
4. **Precedent**: This mirrors enterprise proxy deployments where client systems are explicitly configured to trust the corporate CA. The pattern is well-understood and widely accepted.

**What remains transparent:** The identity injection itself — the signing, the header addition, the audit logging — requires no agent cooperation and cannot be disabled by the agent. The agent's awareness extends only to the TLS trust configuration, not to the identity mechanism.

---

## 3. Cryptographic Mechanisms

### 3.1 Canonical String Construction

For each outgoing HTTP request, a canonical string is constructed as follows:

```
canonical = "{method}\n{url}\n{body_hash}\n{timestamp}\n{nonce}"
```

Where:
- `method`: The HTTP method in uppercase (GET, POST, PUT, DELETE, etc.)
- `url`: The complete request URL including query parameters
- `body_hash`: SHA-256 hash of the request body (hex-encoded), or SHA-256 of empty string for bodyless requests
- `timestamp`: ISO 8601 timestamp with timezone (e.g., `2026-03-02T12:00:00Z`)
- `nonce`: UUID v4, unique per request

**Example:**
```
POST
https://api.example.com/v1/data?page=1
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
2026-03-02T12:00:00Z
550e8400-e29b-41d4-a716-446655440000
```

#### 3.1.1 Normative Canonicalization Specification

The canonical string construction described above requires precise normalization rules to ensure that independently implemented signers and verifiers produce identical canonical strings for the same logical request. This section provides the normative specification in ABNF (RFC 5234).

**ABNF Grammar:**

```abnf
canonical-string = method LF url LF body-hash LF timestamp LF nonce

method           = 1*UPALPHA
                 ; HTTP method in uppercase: "GET", "POST", "PUT",
                 ; "DELETE", "PATCH", "HEAD", "OPTIONS"

url              = scheme "://" authority path-abempty ["?" query]
                 ; Fully normalized URL per rules below

body-hash        = 64HEXDIG
                 ; Lowercase hex-encoded SHA-256 of request body
                 ; For bodyless requests: SHA-256 of empty string
                 ; = "e3b0c44298fc1c149afbf4c8996fb924
                 ;    27ae41e4649b934ca495991b7852b855"

timestamp        = date-fullyear "-" date-month "-" date-mday
                   "T" time-hour ":" time-minute ":" time-second "Z"
                 ; ISO 8601 UTC only, no timezone offset variants

nonce            = 8HEXDIG "-" 4HEXDIG "-" "4" 3HEXDIG "-"
                   variant 3HEXDIG "-" 12HEXDIG
                 ; UUID v4 in lowercase canonical form (RFC 9562)

variant          = %x38-39 / %x61-62
                 ; '8', '9', 'a', or 'b'

LF               = %x0A  ; Line Feed (not CRLF)

UPALPHA          = %x41-5A  ; A-Z

HEXDIG           = DIGIT / %x61-66  ; 0-9, a-f (lowercase only)
```

**URL Normalization Rules:**

The URL component MUST be normalized before inclusion in the canonical string. The following rules are applied in order:

1. **Scheme**: Lowercase. `HTTPS` → `https`.
2. **Host**: Lowercase. `API.Example.COM` → `api.example.com`.
3. **Port**: Omit default ports. `https://api.example.com:443/` → `https://api.example.com/`. Non-default ports are preserved: `https://api.example.com:8443/`.
4. **Path**: Resolve `.` and `..` segments (RFC 3986 Section 5.2.4). Preserve trailing slash. Percent-encode reserved characters per RFC 3986. Decode unreserved characters: `%41` → `A`. Normalize percent-encoding to uppercase: `%2f` → `%2F`.
5. **Query Parameters**: Sort lexicographically by key, then by value for duplicate keys. Preserve empty values: `key=` is distinct from `key`. Percent-encode consistently per rule 4.
6. **Fragment**: Remove entirely. Fragment identifiers (`#section`) are never sent to the server and MUST NOT be included.

**Normalization Examples:**

```
Input:  HTTPS://API.Example.COM:443/v1/Data/../users?page=2&count=10&page=1
Output: https://api.example.com/v1/users?count=10&page=1&page=2

Input:  https://api.example.com/search?q=hello+world&lang=en#results
Output: https://api.example.com/search?lang=en&q=hello+world

Input:  https://api.example.com:8443/v1/data?
Output: https://api.example.com:8443/v1/data
```

**Body Hash Rules:**

1. The body hash MUST be computed over the raw request body bytes, not a decoded or parsed representation.
2. For requests with no body (GET, HEAD, DELETE without body, OPTIONS), the hash MUST be the SHA-256 of the zero-length byte string: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
3. For requests with `Content-Encoding` (e.g., gzip), the hash is computed over the compressed body as transmitted.
4. The hash MUST be hex-encoded in lowercase.

**Timestamp Rules:**

1. Timestamps MUST be in UTC, indicated by the `Z` suffix.
2. Offset variants (`+00:00`, `-05:00`) MUST NOT be used.
3. Fractional seconds MUST NOT be included. Truncate to whole seconds.
4. Verifiers MUST accept timestamps within a ±30 second window of their own clock.
5. Implementations SHOULD use NTP-synchronized clocks with drift ≤1 second.

**Nonce Rules:**

1. Nonces MUST be UUID v4 (RFC 9562) in lowercase canonical form.
2. Verifiers MUST reject previously-seen nonces within the timestamp validity window.
3. Nonce storage MAY be pruned for entries older than 60 seconds (2× the timestamp window).

**Canonical String Assembly:**

The five components are joined by a single Line Feed character (`0x0A`). No trailing Line Feed is appended. The resulting string is encoded as UTF-8 before signing.

**Relationship to IETF HTTP Message Signatures (RFC 9421):**

RFC 9421 defines a general mechanism for HTTP message signing with component identifiers and signature parameters. Elpis deliberately uses a simplified canonical string rather than adopting RFC 9421 directly, for the following reasons:

1. **Simplicity**: Elpis signs 5 fixed fields. RFC 9421 requires negotiating which components to sign, managing `@signature-params`, and handling derived components — complexity that serves no purpose when the signer and the identity mechanism are co-located in the proxy.
2. **Proxy Transparency**: RFC 9421 requires the signer to select headers for inclusion. Since Elpis signs at the proxy layer before headers reach the destination, some headers may not yet exist (e.g., `Content-Length` after chunked encoding). A self-contained canonical string avoids this ordering dependency.
3. **Determinism**: RFC 9421's flexibility introduces ambiguity — different implementations may select different components. Elpis' fixed canonical format guarantees identical inputs across all implementations.

Future protocol versions MAY adopt RFC 9421 component identifiers if interoperability with HTTP Message Signatures ecosystems becomes desirable. The current design prioritizes implementation simplicity and verification determinism.

### 3.2 Ed25519 Signature

The canonical string is signed using the Ed25519 digital signature algorithm (RFC 8032):

```
signature = Ed25519_Sign(private_key, encode_utf8(canonical))
```

The resulting signature is Base64-encoded for inclusion in the HTTP header.

**Why Ed25519:**
- Deterministic signatures (no nonce generation required beyond our explicit nonce)
- 128-bit security level
- Fast verification (~70,000 verifications per second on commodity hardware)
- Small key sizes (32 bytes public, 64 bytes private)
- Used natively by the XRP Ledger for transaction signing
- Resistant to timing attacks by design

### 3.3 Key Management

Each agent's Ed25519 key pair is generated during agent provisioning (not by the agent itself) and stored in Redis:

```
Key: cert:{did}
Value: {
    "public_key": "<hex-encoded Ed25519 public key>",
    "private_key": "<encrypted Ed25519 private key>",
    "certificate": "<agent certificate>",
    "cert_hash": "<SHA-256 of certificate>",
    "provider": "<provider domain>",
    "issued_at": "<ISO 8601>",
    "expires_at": "<ISO 8601>"
}
```

**Security properties:**
- Private keys never leave the proxy container.
- Keys are not accessible to the agent.
- Key rotation is performed by the provider, not the agent.
- Compromised keys can be revoked on-chain within seconds.

### 3.4 Injected Header Schema

Every outgoing request from an identified agent container receives the following headers:

```http
X-Elpis-DID: did:xrpl:rN7n3473SaZBCG4dFL83w7p1C9zBomYy1V#a7f3b2c1
X-Elpis-Signature: <Base64-encoded Ed25519 signature>
X-Elpis-Timestamp: 2026-03-02T12:00:00Z
X-Elpis-Nonce: 550e8400-e29b-41d4-a716-446655440000
X-Elpis-Cert-Hash: sha256:a1b2c3d4e5f6...
X-Elpis-Domain: provider-name.elpis
X-Elpis-Display-Name: <optional human-readable agent name>
X-Elpis-Scope: <optional scope identifier>
```

| Header | Purpose | Validation |
|---|---|---|
| `X-Elpis-DID` | Agent's W3C Decentralized Identifier | Format check, XRPL lookup |
| `X-Elpis-Signature` | Ed25519 signature of canonical string | Verify with public key |
| `X-Elpis-Timestamp` | Signature creation time | Must be within ±30 seconds |
| `X-Elpis-Nonce` | Unique request identifier | Must not be previously seen (replay protection) |
| `X-Elpis-Cert-Hash` | Hash of signing certificate | Must match on-chain certificate |
| `X-Elpis-Domain` | Provider domain | Must match DID's provider |
| `X-Elpis-Scope` | Optional access scope | Application-dependent |

### 3.5 Signature Verification

A receiving service validates an Elpis-signed request as follows:

1. Extract the canonical string components from the request (method, URL, body, timestamp from header, nonce from header).
2. Reconstruct the canonical string.
3. Retrieve the public key associated with the DID (from XRPL or cache).
4. Verify the Ed25519 signature against the canonical string using the public key.
5. Check that the timestamp is within the acceptable window (±30 seconds).
6. Check that the nonce has not been previously seen (replay protection).
7. Verify that the certificate hash matches the current valid certificate on-chain.
8. Check that the DID has not been revoked.

Total validation time: <5ms with cached credentials.

### 3.6 Credential Caching Architecture

On-chain credential lookups (XRPL network round-trip) take 500ms–2s, making real-time per-request validation impractical. Elpis therefore implements a three-layer caching architecture:

**Layer 1 — Boot Cache**: On proxy/gateway startup, all credentials for configured trusted domains are bulk-loaded from the XRPL via `account_objects` queries. Selectors include: per trusted domain (all agents of a provider), per owner wallet (all agents of a customer), or wildcard (all known domains). Typical boot time: 2–5 seconds.

**Layer 2 — Live Cache**: An XRPL WebSocket subscription monitors credential transactions in real-time. `CredentialCreate` events add entries to the cache immediately. `CredentialDelete` events (revocation) invalidate entries immediately. This ensures the cache reflects ledger state within one ledger close (~3–5 seconds).

**Layer 3 — Periodic Sync**: A full reconciliation runs every 5 minutes as a safety net for missed WebSocket events. Any cache entry not confirmed by the ledger is evicted. This guarantees eventual consistency even under network partition.

**Cache storage** uses Redis with the following key schema:

```
cert:{did}          → Certificate + public key + cert hash + expiry
provider:{domain}   → Provider CA + list of agent DIDs
revoked:{did}       → Revocation marker (TTL: 24h)
nonce:{nonce}       → Seen nonces (TTL: 60s, replay protection)
```

**Cache invalidation for revocation** is the critical path: WebSocket push triggers immediate Redis deletion, and a `revoked:{did}` marker is set to reject requests even if the credential is re-fetched before the periodic sync runs. All cache entries carry a maximum TTL (default: 5 minutes) as a fail-safe — if the WebSocket connection is lost, entries expire automatically rather than serving stale data.

**Performance by scenario:**

| Scenario | Latency |
|---|---|
| Agent in cache (normal operation) | <1ms |
| Agent not cached, trusted domain known | ~500ms (one-time XRPL lookup, then cached) |
| Completely unknown agent | ~1–2s (XRPL lookup + chain verification) |
| Revoked agent | <1ms (revocation marker in cache) |

---

## 4. XRP Ledger Integration

### 4.1 Agent Identity on the Ledger

Each agent's identity is anchored on the XRP Ledger through three mechanisms:

**Multi-Purpose Token (MPT):** Each agent receives a unique MPT issued by the owner's wallet. The MPT serves as the on-chain identity token — proof that the agent exists and is owned by a specific entity.

**W3C Decentralized Identifier (DID):** The agent's DID follows the format `did:xrpl:{owner_address}#{agent_id}`, where `agent_id` is an opaque, provider-generated identifier (typically a UUID short form). The DID is derived from the owner's XRPL address, establishing a cryptographic link between agent and owner without requiring a separate wallet for each agent. Importantly, the agent identifier is opaque by design — it does not reveal the agent's internal name, purpose, or configuration. Providers may optionally publish a human-readable display name via the agent's Verifiable Credential, but this is an explicit opt-in, not a default.

**Verifiable Credentials:** Agent properties (role, capabilities, compliance status, certification level, flags) are expressed as W3C Verifiable Credentials stored on the XRPL using the Credentials feature (XLS-70).

### 4.2 Certificate Authority Architecture

Elpis implements a three-tier certificate authority:

```
Root CA (Multi-Sig, up to 32 signers)
  └── Provider CA (certified by Root CA)
        └── Agent Certificate (certified by Provider CA)
              └── User Wallet (optional, for user-agent binding)
```

**Root CA:** Operated as a multi-signature entity requiring M-of-N signatures for any operation. This prevents single points of compromise and enables governance through distributed trust.

**Provider CA:** Each agent provider operates a Provider CA, certified by the Root CA. The Provider CA issues and manages certificates for all agents under the provider's control.

**Agent Certificate:** Each agent receives a certificate from its Provider CA, containing the agent's public key, capabilities, and validity period. Certificate renewal is automatic; revocation is immediate.

### 4.3 Revocation

Revocation can occur at any level of the trust chain:

| Level | Action | Effect | Time |
|---|---|---|---|
| Agent | Revoke agent certificate | Single agent loses identity | ~5 seconds |
| Provider | Revoke provider CA | All provider's agents lose identity | ~5 seconds |
| Root | Revoke root signer | Depends on multi-sig threshold | ~5 seconds |
| User | Revoke user wallet | User can no longer command agents | ~5 seconds |

Revocation is propagated through:
1. **XRPL Credential deletion**: Immediate, globally visible
2. **Redis PUB/SUB**: Real-time notification to all proxy instances
3. **Proxy cache invalidation**: Cached credentials are invalidated immediately
4. **Active session termination**: Existing sessions for revoked agents are terminated

### 4.4 Flagging System

Elpis implements a graduated flagging system using XRPL Credentials:

| Level | Meaning | Effect |
|---|---|---|
| None | No flags | Full access |
| Info | Informational notice | Logged, no restriction |
| Warning | Behavioral concern | Limited capabilities |
| Critical | Severe violation | Immediate access revocation, credential revoke |

Flags are stored as Verifiable Credentials on the XRPL and are publicly queryable. A critical flag triggers automatic credential revocation, rendering the agent's identity invalid within seconds.

---

## 5. Chain of Trust

### 5.1 Complete Trust Chain

Elpis establishes a complete chain of trust from the root authority to the end user:

```
Root CA (XRPL Multi-Sig)
  │
  ├── Certifies → Provider CA (EFINITI, other providers)
  │                   │
  │                   ├── Certifies → Agent Certificate (sisyphus, amphiaraus, ...)
  │                   │                   │
  │                   │                   └── Signs → Every outgoing HTTP request
  │                   │
  │                   └── Certifies → Agent Certificate (other agents)
  │
  └── Certifies → Provider CA (other providers)
                      └── ...

User Identity:
  Social OAuth + MFA → Account Wallet (Ed25519) → KYC (external) → Signed commands to agents
```

### 5.2 Trust Chain in Every Message

Every outgoing request from an agent carries the complete certificate chain as intermediate certificates, analogous to TLS certificate chains:

```http
X-Elpis-Chain: <Base64-encoded certificate chain>
```

This allows any recipient to verify the complete chain of trust — from the agent's signature through the provider's certification to the root authority — without needing to contact any external service.

### 5.3 User Identity

To close the trust circle, user commands to agents are also signed:

1. User authenticates via Social OAuth + MFA
2. User receives an Ed25519 account wallet (derived, not a blockchain wallet)
3. Optional: External KYC verification (SumSub, Onfido, Veriff)
4. Every command from user to agent is signed with the user's wallet key
5. The agent's MCP (Model Context Protocol) validates the signature before delivering the command to the LLM

This creates a fully bidirectional chain: the user can verify the agent's identity, and the agent can verify the user's identity.

---

## 6. Security Analysis

### 6.1 Threat Model

| Attack Vector | Protection |
|---|---|
| Man-in-the-Middle | Ed25519 signature covers body + timestamp; modification invalidates signature |
| Replay Attack | Timestamp window (±30s) + unique nonce per request |
| Identity Spoofing | Requires Ed25519 private key (never leaves proxy container) + valid certificate chain |
| Token/Certificate Theft | Certificate without private key is useless for signing |
| Prompt Injection ("act anonymously") | Identity is in infrastructure, not in prompt; agent cannot disable proxy |
| Rogue Agent (compromised) | On-chain revocation in seconds; all active sessions terminated |
| Rogue Provider (compromised) | Root CA revokes Provider CA; all provider's agents immediately invalid |
| Label Manipulation | Docker labels are immutable after container creation; agent has no Docker socket access |
| Proxy Bypass | Agent's only network route is through the proxy (HTTP_PROXY env vars) |
| Key Extraction from Redis | Redis access controlled; keys encrypted at rest; HSM integration on roadmap |

### 6.2 The Single True Vulnerability

If the infrastructure operator's host is fully compromised (root access to the machine running the proxy containers), the attacker gains access to the signing keys. Mitigations:

1. **HSM (Hardware Security Module)**: Keys stored in hardware, not extractable (see Section 6.2.1)
2. **TEE (Trusted Execution Environment)**: Signing operations isolated in hardware enclaves (see Section 6.2.1)
3. **Key Rotation**: Regular rotation limits the window of compromise
4. **Monitoring**: Anomaly detection on signing patterns
5. **Revocation**: Compromised keys can be revoked on-chain in seconds

#### 6.2.1 Hardware-Backed Key Management: TEE and HSM Integration

In the current reference implementation, Ed25519 private keys are stored encrypted-at-rest in Redis. An attacker with root access can: (1) read process memory of the proxy to extract decrypted keys during signing operations, (2) access the Redis instance and attempt offline decryption of stored keys, or (3) intercept key material during key rotation. Hardware-backed key management addresses all three vectors by ensuring private keys **never exist in extractable form in host memory**.

**Path 1: Hardware Security Modules (HSM)**

For cloud-deployed providers, managed HSM services offer the lowest barrier to hardware-backed keys:

| Provider | Service | Ed25519 Support | Integration |
|---|---|---|---|
| AWS | CloudHSM / KMS | KMS: Ed25519 natively (2024+); CloudHSM: via PKCS#11 | Sign API call per request |
| Google Cloud | Cloud HSM (via Cloud KMS) | Ed25519 via `EC_SIGN_ED25519` | Sign API call per request |
| Azure | Managed HSM / Key Vault | Ed25519 via Key Vault Premium | Sign API call per request |
| Thales | Luna Network HSM | Ed25519 via firmware ≥7.8 | PKCS#11 or JCA |
| YubiHSM 2 | USB HSM | Ed25519 natively | yubihsm-connector SDK |

The proxy stores only a **key reference** (HSM key ID) in Redis, not the private key. Signing operations are delegated to the HSM via API call. Even full host compromise yields only key references that are useless without HSM authentication. Cloud HSM sign operations add 2-10ms latency per request — negligible for autonomous agent HTTP requests.

**Path 2: Trusted Execution Environments (TEE)**

Intel Software Guard Extensions (SGX) and Trust Domain Extensions (TDX) provide hardware-isolated enclaves where code and data are protected from the host OS, hypervisor, and even physical access. The signing enclave: (1) generates the Ed25519 key pair inside the enclave during agent provisioning, (2) seals the private key to the enclave identity, (3) exposes a single `sign(canonical_string) → signature` interface, and (4) never exports the private key — not even to the proxy process itself. Even with root access, the attacker cannot read enclave memory.

AWS Nitro Enclaves provide an equivalent isolated compute environment with no persistent storage, no network access, and no interactive access — even for the root user of the parent instance. Key material is encrypted with AWS KMS and can only be decrypted inside the enclave (KMS policy restricts decryption to the enclave's attestation document).

**Path 3: Hybrid Approach (Recommended)**

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

**Attestation Chain Extension:** TEE-based deployments enable an additional trust property: **hardware attestation**. The enclave can produce a cryptographic attestation document proving: (1) the signing code is the expected, unmodified Elpis proxy enclave, (2) the enclave is running on genuine hardware, and (3) the key was generated inside the enclave and has never been exported. This attestation can be included in the Elpis certificate metadata, allowing verifiers to confirm not just *who* signed a request, but that the signing infrastructure itself has not been tampered with.

**Migration Path:** Upgrading from Tier 1 to Tier 2/3 requires deploying the new key store backend, generating new key pairs in the hardware-backed store, and rotating the agent's on-chain certificate. No changes to the agent, the proxy's signing logic, or the verification protocol are required — a direct consequence of the "identity without cooperation" design.

### 6.3 Why This Cannot Be Circumvented by the Agent

The agent cannot bypass the identity injection because:

1. **No direct network route**: Network-level enforcement ensures all traffic transits the proxy regardless of agent behavior. The enforcement is layered: (a) `HTTP_PROXY`/`HTTPS_PROXY` environment variables direct cooperative clients, (b) iptables/nftables rules at the host level block all direct outbound traffic from agent network namespaces except to the proxy endpoint (e.g., `iptables -A OUTPUT -m owner --uid-owner agent -j DROP` combined with `-A OUTPUT -d proxy-ip -p tcp --dport 8080 -j ACCEPT`), and (c) in Kubernetes environments, CNI NetworkPolicy or egress gateway configurations provide equivalent enforcement. Even if an agent clears proxy environment variables or uses raw sockets, the kernel-level firewall rules prevent direct internet access.
2. **No runtime API access**: The agent has no access to the container runtime daemon (Docker socket, Kubernetes API, LXC API, Proxmox API) and cannot modify its own metadata, network configuration, or container settings. This is a fundamental property of container isolation, not specific to any single runtime.
3. **No key access**: The Ed25519 signing keys are stored in the proxy's key store (Redis or equivalent), not in the agent's container.
4. **Audit trail**: Even if the proxy fails, the absence of expected headers is itself a signal that can trigger alerts.

---

## 7. Integration with Existing Standards

Elpis does not replace existing authentication and authorization standards. It fills the identity gap beneath them:

| Standard | Relationship to Elpis |
|---|---|
| **OAuth 2.0** | Elpis provides the identity layer under OAuth. Three integration paths: custom JWT claim, identity provider, mutual TLS (RFC 8705) |
| **MFA** | Elpis provides a multi-layer cryptographic trust equivalent for agents: private key (knowledge factor) + certificate chain (possession factor) + immutable XRPL anchor (public verifiability factor) |
| **OpenID Connect** | Elpis can function as an OIDC identity provider |
| **SAML 2.0** | Elpis certificates can be embedded as SAML attributes |
| **W3C DIDs/VCs** | Elpis builds natively on W3C DID Core v1.0 and Verifiable Credentials v2.0 |
| **mTLS (RFC 8705)** | Elpis certificates can serve as client certificates in OAuth mutual TLS |

---

## 8. Implementation and Validation

### 8.1 Reference Implementation

The Elpis reference implementation is deployed in the Pandora multi-agent platform operating 12+ autonomous AI agents:

**Elpis Proxy** (Python/asyncio):
- aiohttp-based transparent forward proxy
- TLS interception (SSL Bump) with dynamic per-domain certificate generation and LRU cache
- PyNaCl for Ed25519 signing
- docker-py for container identification via Docker API
- Redis for certificate and key storage
- Proxy CA generation with encrypted private key storage
- Automatic Ed25519 key provisioning for new agents

**Elpis Validator** (Python/FastAPI):
- Demo web service that reads and displays Elpis headers
- Zero-login authentication for Elpis-identified agents
- Dashboard with four status indicators (certificate, provider, flagging, trust score)
- Admin panel with XRPL testnet validation and flagging controls
- 5-layer middleware stack (Elpis detection, CSRF, authentication, flagging, access control)

**Elpis Certificate Authority**:
- Root CA with multi-signature support (up to 32 signers)
- Provider CA with agent certification and revocation
- Gateway validation achieving <5ms latency
- Redis-based state persistence
- Svelte frontend with 9 pages

### 8.2 Validation Results

End-to-end testing demonstrated:

1. **Automatic identification**: An AI agent navigating to the Elpis Validator web service via Selenium was automatically identified through Elpis headers without any login mechanism.
2. **Header completeness**: All six X-Elpis-* headers were correctly injected and displayed.
3. **Access control**: The agent was correctly granted dashboard access but denied admin access.
4. **API verification**: The `/api/status` endpoint correctly returned `elpis_detected: true` with all identity fields.
5. **Flagging**: Setting a critical flag in the admin panel resulted in the agent receiving a 403 response within 5 seconds.
6. **XRPL verification**: The agent's DID was successfully validated against the XRPL testnet, confirming the on-chain identity anchor.

### 8.3 Performance

| Operation | Latency |
|---|---|
| Proxy header injection | <1ms |
| Ed25519 signature computation | <0.5ms |
| Gateway signature verification | <1ms |
| Credential cache lookup | <0.5ms |
| Total gateway validation | <5ms |
| On-chain revocation propagation | ~5 seconds |

---

## 9. Related Work

### 9.1 Machine Identity Management

Existing machine identity solutions address service-to-service authentication within controlled environments. SPIFFE/SPIRE [9] provides workload identity through SVID (SPIFFE Verifiable Identity Document) certificates issued to processes based on attestation. HashiCorp Vault [10] manages secrets and dynamic credentials for machine-to-machine communication. Cloud-native solutions (AWS IAM Roles, Google Service Accounts, Azure Managed Identities) offer provider-specific identity within their ecosystems.

These systems share a common assumption: the workload cooperates with the identity mechanism. SPIFFE requires a SPIRE agent sidecar; Vault requires API calls for credential retrieval; cloud IAM requires SDK integration. Elpis differs fundamentally in requiring zero cooperation from the agent process — identity is injected at the network layer without the agent's awareness or consent. Additionally, none of these systems provide publicly verifiable, cross-organizational identity: a SPIFFE SVID is meaningful within the issuing trust domain but cannot be independently verified by an external party without federation agreements.

#### 9.1.1 Detailed Comparison: SPIFFE/SPIRE, Istio, and Elpis

The most mature machine identity framework — SPIFFE (Secure Production Identity Framework for Everyone) with its reference implementation SPIRE — shares surface-level goals with Elpis but differs fundamentally in architecture, trust model, and scope. The following comparison clarifies why Elpis is not "SPIFFE for agents" but addresses a categorically different problem.

**Architectural Comparison:**

| Dimension | SPIFFE/SPIRE | Istio Service Mesh | Elpis |
|---|---|---|---|
| **Identity Model** | SVID (x509 or JWT) issued to workloads | mTLS certificates via Citadel/Istiod | DID + Ed25519 signature per request |
| **Identity Scope** | Within a single trust domain; cross-domain requires federation | Within a single mesh; multi-mesh requires complex peering | Globally verifiable via XRPL; no federation required |
| **Agent Cooperation** | Required — SPIRE agent sidecar must run alongside workload | Required — Envoy sidecar injected into pod | **Not required** — identity injected transparently at proxy layer |
| **Attestation** | Node attestation (AWS IID, K8s SAT, etc.) + workload attestation (Unix PID, K8s pod, Docker labels) | K8s service account identity via Istiod | Container runtime metadata (Docker labels, K8s annotations, LXC properties) read by proxy |
| **Key Storage** | SPIRE agent manages SVIDs; rotated automatically | Envoy sidecar holds short-lived certs from Istiod | Proxy-side key store (Redis); agent has zero key access |
| **Revocation** | CRL/OCSP; depends on CA infrastructure; propagation delay varies | Certificate rotation (short-lived certs, ~24h) | On-chain revocation in 3–5 seconds; globally visible |
| **Public Verifiability** | No — SVIDs meaningful only within trust domain | No — mesh-internal only | **Yes** — any party can verify via XRPL lookup |
| **Deployment Model** | Sidecar per node (SPIRE agent) + central SPIRE server | Sidecar per pod (Envoy) + control plane (Istiod) | Single forward proxy per provider; shared across all agents |
| **Runtime Support** | Primarily Kubernetes; extensible via plugins | Kubernetes-native; limited outside K8s | Runtime-agnostic (Docker, Podman, LXC, K8s, bare-metal) |
| **LLM/AI Agent Awareness** | None — designed for microservices | None — designed for microservices | Purpose-built for autonomous AI agents |
| **Prompt Injection Resistance** | N/A — identity is software-level, accessible to workload | N/A — Envoy is a sidecar, not a network-level proxy | **Yes** — agent cannot access, modify, or disable identity injection |

**The Fundamental Distinction:**

SPIFFE and Istio solve **service-to-service authentication within controlled environments**. They answer the question: "Is this microservice who it claims to be?" The workload is assumed to be a known, deployed, cooperating piece of software.

Elpis solves **autonomous actor identification across organizational boundaries**. It answers a different question: "Who is responsible for this AI agent's actions?" The agent is assumed to be an autonomous, potentially unpredictable actor that must not participate in its own identification.

This distinction has three concrete consequences:

1. **Cooperation vs. Transparency**: SPIFFE requires a running SPIRE agent process; if the workload kills the sidecar or manipulates its environment, identity breaks. Elpis operates at the network layer — the agent has no mechanism to interfere.

2. **Internal vs. External Trust**: A SPIFFE SVID is a credential within an organizational boundary. Presenting an SVID to an external party requires bilateral federation agreements. An Elpis signature is independently verifiable by any party with internet access — the trust anchor is a public ledger, not a private CA.

3. **Static vs. Autonomous**: SPIFFE identifies deployed services with predictable behavior. Elpis identifies autonomous agents whose behavior is non-deterministic — making the "identity without cooperation" property not just convenient but essential.

**When to Use What:**

- **SPIFFE/SPIRE**: Internal microservice authentication, CI/CD workload identity, cloud-native service mesh — where all parties are within a single trust domain and workloads cooperate.
- **Istio**: Kubernetes-native service mesh with traffic management, observability, and mTLS — within a single cluster or mesh.
- **Elpis**: AI agent identification across organizational boundaries, where agents are autonomous, public verifiability is required, and the agent must not participate in its own identity management.

These are complementary, not competing. An Elpis-identified agent running inside a SPIFFE trust domain would carry both identities: SPIFFE for internal service mesh authentication, Elpis for external cross-organizational accountability.

### 9.2 AI Safety and Alignment

The AI safety community has focused on controlling agent behavior through guardrails, RLHF, content filtering, and sandboxing [11]. These approaches are complementary to Elpis but operate at a fundamentally different layer. Guardrails attempt to constrain what an agent *can do*; Elpis ensures that whatever an agent *does do* is cryptographically attributed to a verifiable identity. The distinction is between prevention (software-level, circumventable via jailbreaks and prompt injection) and attribution (infrastructure-level, not circumventable by the agent).

Recent work on AI agent frameworks — including Anthropic's Model Context Protocol (MCP), Google's Agent-to-Agent Protocol (A2A), and OpenAI's function calling — focuses on capability and interoperability rather than identity. These frameworks define *what* agents can do and *how* they communicate, but not *who* they are. Elpis provides the missing identity layer that these frameworks can build upon.

### 9.3 Blockchain-Based Identity

W3C DIDs [2] and Verifiable Credentials [3] provide the foundational standards for decentralized identity. Projects like Sovrin, ION (Bitcoin-anchored), and Ceramic focus primarily on human identity and self-sovereign identity (SSI). Elpis extends these standards specifically for AI agents, adding the transparent proxy injection mechanism and the passport model that are unique to the agent identity use case. The choice of XRPL as the anchoring ledger is motivated by its 3-5 second finality, native Credential support (XLS-70), Multi-Purpose Tokens, and Permissioned Domains — features that map directly to the requirements of agent identity management without requiring smart contract development.

### 9.4 Zero Trust Architecture

Google's BeyondCorp [12] established the principle that network location should not grant implicit trust. NIST SP 800-207 [13] formalized Zero Trust Architecture (ZTA) principles. Elpis aligns with ZTA philosophy — every request carries proof of identity regardless of network origin — but extends it to a class of actors (autonomous AI agents) that ZTA was not designed to address. Traditional ZTA assumes human users authenticating through identity providers; Elpis provides the equivalent identity mechanism for non-human autonomous actors.

### 9.5 HTTP Message Signatures and Request Signing Standards

The IETF HTTP Message Signatures specification (RFC 9421) defines a standardized mechanism for signing HTTP requests and responses using existing HTTP semantics. The specification addresses canonicalization, signature base construction, and key binding — problems that overlap with Elpis's canonical string construction (Section 3.1).

Elpis deliberately does not adopt HTTP Message Signatures for several architectural reasons: (1) RFC 9421 is designed for application-level signing where the signer is the HTTP client or server — Elpis signs at the infrastructure level where the proxy, not the agent, is the signer; (2) the specification assumes the signer has access to the application's HTTP context, while the Elpis proxy operates on intercepted traffic and must construct signatures from the proxied request; (3) Elpis's header schema carries agent identity metadata (DID, provider, trust chain) that has no equivalent in RFC 9421's signature parameters.

However, Elpis's canonicalization approach would benefit from adopting RFC 9421's rigor in specifying signature base construction, particularly regarding URL normalization, header field ordering, and handling of duplicate headers. A future revision of the Elpis specification should either formally adopt RFC 9421 components or provide an equally normative canonicalization specification.

### 9.6 Alternative DID Methods and Trust Anchors

The choice of `did:xrpl` as Elpis's DID method warrants comparison with alternatives:

| DID Method | Trust Anchor | Revocation Speed | Public Verifiability | Operational Cost |
|---|---|---|---|---|
| `did:xrpl` (Elpis) | XRPL public ledger | ~5s (ledger finality) | Full (public ledger) | Low (reserve + tx fees) |
| `did:web` | DNS + HTTPS | Minutes–hours (DNS TTL) | Partial (server availability) | Hosting costs |
| `did:key` | None (self-certifying) | Not revocable | Full (no resolution needed) | None |
| `did:ion` | Bitcoin | ~60 min (block finality) | Full (public ledger) | High (Bitcoin tx fees) |
| `did:ethr` | Ethereum | ~15s (block finality) | Full (public ledger) | Variable (gas fees) |

`did:web` is the simplest and most widely adopted method, anchoring DIDs to web domains via HTTPS. For Elpis, `did:web` is insufficient because: (a) revocation depends on DNS TTL propagation (minutes to hours vs. XRPL's 3-5 seconds), (b) availability depends on the DID controller's web server (a single point of failure), and (c) there is no inherent tamper-evidence — a compromised server can silently alter DID documents. `did:key` provides no revocation mechanism at all. `did:ion` offers strong guarantees but with 60-minute finality, which is unacceptable for real-time agent identity revocation.

Sigstore (Fulcio/Rekor) offers an alternative model: ephemeral certificates with transparency log entries. This approach is well-suited for software artifact signing but lacks the persistent identity semantics required for agents that operate continuously and need stable, long-lived identities with real-time revocation capability.

### 9.7 Emerging Standardization

The field of AI agent identity is converging rapidly. The W3C AI Agent Protocol Community Group (established May 2025) is developing standards for agent interoperability, including identity aspects [14]. An IETF Internet-Draft on security considerations for AI agents (Sogomonian, September 2025) addresses authentication and authorization challenges [15]. These efforts validate the problem space Elpis addresses. Elpis contributes a concrete, implemented solution — particularly the transparent proxy injection pattern and infrastructure-level identity binding — that complements these emerging standards rather than competing with them.

---

## 10. Discussion

### 10.1 Adoption Path

Elpis is designed for gradual adoption with a self-reinforcing dynamic analogous to HTTPS adoption:

1. **Phase 1 — Optional Identity**: Provider adds proxy to existing agent deployments (one configuration change). Agents are identified; recipients ignore headers. No disruption.
2. **Phase 2 — Preferential Treatment**: Early-adopter services begin validating Elpis headers, offering preferential access to identified agents: faster response times, higher rate limits, reduced verification requirements, premium API tiers.
3. **Phase 3 — Traffic Classification**: Services begin classifying traffic as *identified* (Elpis headers present and valid), *legacy* (human traffic without Elpis, treated normally), or *unidentified* (automated traffic without Elpis headers — treated with reduced trust, higher latency, additional verification). This mirrors how browsers began marking HTTP sites as "Not Secure."
4. **Phase 4 — De Facto Standard**: Unidentified agent traffic becomes impractical, analogous to HTTP in a post-HTTPS world. Even agents previously running without identity (e.g., CLI tools, local scripts) adopt Elpis voluntarily because the alternative — being classified as untrusted anonymous traffic — carries real costs.

**The self-reinforcing dynamic:** As more recipients validate Elpis headers, identified agents gain tangible advantages. As identified agents become the norm, unidentified traffic becomes suspicious. This creates market pressure for adoption without requiring regulatory mandates — though regulatory pressure (EU AI Act) accelerates the timeline.

**Trust gradient:** Within Elpis-identified traffic, a further gradient emerges based on the agent's trust properties: KYC level of the owner (none/basic/enhanced/full), trust score history, flagging status, and provider reputation. An Elpis-identified agent with full KYC receives premium treatment. An Elpis-identified agent with no KYC is still trusted more than an unidentified agent. No Elpis at all becomes the new HTTP.

### 10.2 Limitations

1. **Proxy as single point**: The proxy must be available for agents to communicate. Mitigated by redundancy and failover. In a multi-agent deployment, a proxy outage affects all agents on that host — a blast radius that must be managed through standard high-availability patterns (health checks, automatic restart, load balancing across proxy instances).
2. **Non-HTTP protocols**: Elpis header injection covers all HTTP-based protocols: HTTP, HTTPS (via TLS interception with a proxy CA certificate installed in the agent container), WebSocket (headers in HTTP Upgrade handshake), gRPC (HTTP/2 metadata), and Server-Sent Events. This constitutes >99% of autonomous AI agent communication, as modern APIs, cloud services, messaging platforms, and agent-to-agent protocols (MCP, A2A) are HTTP-based. Non-HTTP protocols (SMTP, FTP, SSH, proprietary TCP) cannot receive injected identity headers but are covered by the proxy's connection-level audit trail (source DID, destination, timestamp).
3. **HTTPS and TLS interception**: HTTPS identity injection requires TLS interception (SSL Bump), which requires the proxy CA to be trusted by all TLS implementations inside the agent container. This is more complex than a single `update-ca-certificates` call: modern toolchains (Python certifi, rustls, Node.js) maintain independent CA stores that must be configured separately via environment variables (see Section 2.5). The recommended mitigation is baking all CA trust configurations into the base container image at build time. While this adds initial setup complexity, it is a one-time cost analogous to enterprise proxy deployments in corporate environments.
4. **Host compromise**: Full host compromise exposes signing keys. Mitigated by HSM integration (on roadmap). Until HSM support is implemented, signing keys are stored in memory within the proxy container — protected by container isolation but not by hardware security boundaries.
5. **Voluntary adoption**: Until regulatory mandates exist, adoption depends on perceived value. The zero-friction deployment model reduces barriers. The EU AI Act (effective August 2025) creates regulatory pressure for agent identification but does not mandate a specific mechanism.
6. **XRPL SignerList maximum**: The XRPL limits SignerLists to 32 entries, capping the Root CA quorum at 32 signers. For the foreseeable future, this is sufficient (the current deployment uses 3 signers in bootstrap phase). At scale, layered multi-signature schemes or off-chain governance voting with on-chain anchoring can extend beyond this limit.
7. **Current validation scope**: The system has been implemented and validated in a single-provider production environment (EFINITI/Pandora, 12+ agents) on the XRPL Testnet. Cross-provider federation, Mainnet deployment, and independent third-party validation remain future milestones. The architecture is designed for these scenarios but they have not yet been empirically validated.
8. **Provider trust centralization**: While the Root CA is decentralized (multi-signature), individual providers manage their agents' signing keys centrally. A compromised or malicious provider could impersonate its own agents. This is mitigated by the certificate chain (provider identity is publicly verifiable) and by the flagging system (anomalous behavior triggers cross-provider alerts), but the trust model inherently relies on provider integrity — analogous to how TLS relies on certificate authority integrity.

### 10.3 Design Principle: Identification Without Restriction

Elpis identifies agents but does not restrict their functionality. This is a deliberate architectural decision:
- **Transparency**: The system provides attribution of actions, not prevention of actions.
- **Provider accountability**: The identity chain makes the deploying provider accountable for agent behavior.
- **Recipient autonomy**: Recipients of agent communications can verify identity and enforce their own access policies.

### 10.4 Elpis Domain Registry: Decentralized Discovery

A critical bootstrapping question for any identity protocol is discovery: how does a participant know which counterparts support the protocol? Elpis addresses this through a decentralized domain registry on the XRP Ledger.

**The problem:** An Elpis-identified agent sends a request to `api.example.com`. Does the destination understand X-Elpis-* headers? Should the agent expect mutual identification? Without a discovery mechanism, Elpis adoption remains opaque — participants cannot find each other.

**The solution: Elpis Domain Registry on XRPL.** Service providers signal Elpis support by publishing a Verifiable Credential on the XRP Ledger:

```
Credential {
  credential_type: "elpis-domain",
  issuer: <provider_wallet>,
  subject: <provider_wallet>,
  uri: "elpis://example.com",
  // Domain verification via DNS TXT record or HTTP .well-known
}
```

This creates a publicly queryable, decentralized registry of Elpis-participating domains — analogous to DNS, but for Elpis capability signaling.

**Caching architecture (DNS-inspired):**

The XRPL is the source of truth, but not the lookup path for every request. The proxy maintains a local cache — conceptually similar to a hosts file:

```
Ledger (truth)  →  Proxy Cache ("Elpis hosts")  →  Request-time decision
                        ↑
                   Sync 4x/day (initially sufficient)
```

| Layer | Purpose | Latency |
|---|---|---|
| Proxy-local cache | Per-request lookup | <1ms |
| Scheduled sync (4x/day) | Ledger → cache reconciliation | Background |
| Peer-to-peer sync (future) | Trusted node exchange without ledger load | Background |
| XRPL lookup (fallback) | Unknown domain, cache miss | 500ms–2s |

As the registry grows, peer-to-peer synchronization between trusted nodes reduces ledger load. The ledger becomes relevant primarily for initial registration, identity verification, and dispute resolution — not for routine lookups.

**Domain verification:** To prevent squatting, domain registration requires proof of control, analogous to SSL certificate issuance:

1. Provider publishes a DNS TXT record: `_elpis.example.com TXT "did:xrpl:{wallet}"`
2. Or serves an HTTP endpoint: `https://example.com/.well-known/elpis.json`
3. A verification service (or peer providers) confirms the binding before the credential is considered valid

**Reference implementation:** The `.well-known/elpis.json` discovery document is live at `https://elpis.efiniti.ai/.well-known/elpis.json`. The schema includes:

```json
{
  "elpis_version": "0.1.0",
  "provider": {
    "name": "Provider Name",
    "domain": "provider.elpis",
    "did": "did:xrpl:{provider_wallet}",
    "website": "https://provider.example.com",
    "contact": "contact@provider.example.com"
  },
  "endpoints": {
    "whoami": "https://provider.example.com/api/whoami",
    "validator": "https://provider.example.com/#validator"
  },
  "capabilities": ["agent-identity", "header-signing", "xrpl-anchoring"],
  "trust": {
    "ca_type": "multi-sig",
    "ledger": "xrpl",
    "signature_algorithm": "Ed25519",
    "header_prefix": "X-Elpis-"
  }
}
```

The `whoami` endpoint provides a live verification tool: any HTTP client sending X-Elpis-* headers receives a JSON response confirming whether the agent was identified, along with the parsed identity fields. This serves as both a debugging tool for agent operators and a public proof of concept for the protocol.

### 10.5 Bidirectional Identity: Closing the Trust Circle

Elpis as described in this paper establishes unidirectional identity: agents prove their identity to recipients. However, the architecture naturally extends to bidirectional identity — recipients proving their identity back to agents.

**The extended model:**

```
Agent → Request with X-Elpis-* headers → Service
        (Agent proves identity)

Service → Response with X-Elpis-* headers → Agent
          (Service proves identity)
```

A service provider (e.g., an e-commerce platform, a financial API, a government service) registers on the Elpis Domain Registry with its own wallet, certificate, and DID. When an Elpis-identified agent sends a request, the service can respond with its own X-Elpis-* headers — proving to the agent that the service is legitimate and Elpis-registered.

**What this enables:**

- **Agent-side trust verification**: Before submitting sensitive data (payment, personal information), an agent verifies the service's on-chain identity. Phishing domains that impersonate legitimate services cannot produce valid Elpis signatures.
- **Mutual authentication without login**: Both parties are cryptographically identified. No cookies, no sessions, no API keys — just infrastructure-level identity in both directions.
- **Trust scoring for services**: Just as agents accumulate trust scores, services accumulate reputation based on their interaction history with identified agents.
- **Closed trust circle**: Owner → Agent → Service → Agent → Owner. Every link in the chain is cryptographically verifiable.

**Relationship to enforcement:** Whether a provider enforces Elpis at the network level (iptables routing through the proxy) or offers it as opt-in is a provider-level implementation decision, not a protocol property. Elpis defines the identity mechanism; enforcement policy is orthogonal. The reference implementation demonstrates network-level enforcement, but the protocol is equally valid in opt-in deployments where agents voluntarily route through the proxy.

### 10.6 Agent-Optimized Content Delivery: Identity as Access Key

Sections 10.4 and 10.5 establish that Elpis enables bidirectional identity between agents and services, and that a decentralized domain registry allows discovery of Elpis-participating endpoints. This section describes a natural extension: services that deliver **optimized content specifically for identified agents**, creating the first concrete economic incentive for Elpis adoption on the recipient side.

**The problem:** When an AI agent browses a conventional website, it receives the same HTML payload as a human user — complete with CSS stylesheets, JavaScript bundles, tracking scripts, advertisements, navigation chrome, and decorative assets. A typical e-commerce product page weighs 200–500KB of HTML, which an LLM must tokenize and parse to extract the relevant information (product name, price, description, available actions). This is profoundly wasteful: the agent spends thousands of tokens — and the agent provider spends real money — processing content designed for human visual consumption.

**The solution: Content negotiation via Elpis identity.** When a web service receives a request with valid X-Elpis-* headers, it can respond with a structured, token-optimized representation of the same content — stripping everything that serves human visual presentation and retaining only the semantic content and available actions.

**Architecture:**

```
Agent Request (with X-Elpis-* headers)
         │
         ▼
┌─────────────────────┐
│   Elpis Gate         │  ← Middleware / Reverse Proxy
│   (Signature Check)  │
└────────┬────────────┘
         │
    ┌────┴────┐
    │ Valid?  │
    └────┬────┘
     Yes │        No
         ▼         ▼
┌──────────────┐  ┌──────────────┐
│ Agent View   │  │ Human View   │
│ (Structured) │  │ (Full HTML)  │
└──────────────┘  └──────────────┘
```

The Elpis Gate operates as a lightweight middleware layer — analogous to how Cloudflare sits in front of existing websites. Existing backend logic remains unchanged; the gate intercepts responses and transforms them for verified agents.

**Response format:** The agent-optimized response replaces rendered HTML with structured content:

```json
{
  "elpis_content": "1.0",
  "page": {
    "title": "Product XY — Premium Widget",
    "url": "https://shop.example.com/products/xy",
    "type": "product",
    "language": "en"
  },
  "content": {
    "description": "Premium widget with stainless steel housing...",
    "price": {"amount": 49.99, "currency": "EUR"},
    "availability": "in_stock",
    "specifications": [
      {"key": "Material", "value": "Stainless Steel"},
      {"key": "Weight", "value": "240g"}
    ]
  },
  "actions": [
    {"id": "add_to_cart", "method": "POST", "url": "/api/cart/add", "params": {"product_id": "xy"}},
    {"id": "check_reviews", "method": "GET", "url": "/api/products/xy/reviews"},
    {"id": "navigate_back", "method": "GET", "url": "/products"}
  ],
  "navigation": [
    {"label": "Home", "url": "/"},
    {"label": "Products", "url": "/products"},
    {"label": "Cart", "url": "/cart", "badge": "3 items"}
  ]
}
```

This format reduces a ~50,000-token HTML page to ~500 tokens of structured content — a **100x reduction** in token consumption. The `actions` array provides an MCP-like interface: the agent knows exactly what it can do without parsing DOM elements or simulating clicks.

**Why Elpis identity is the right gate:**

1. **Not just any bot — a verified agent.** Generic bot detection (User-Agent strings, CAPTCHAs) cannot distinguish a legitimate AI assistant shopping on behalf of its owner from a scraper. Elpis identity provides cryptographic proof of the agent's provenance, its provider's accountability, and its owner's identity chain. The service knows *who* is asking — not just *what* is asking.
2. **Anti-scraping by design.** Serving structured data to unverified requesters would be an open invitation for data harvesting. The Elpis Gate ensures that only agents with verifiable identity — and therefore traceable accountability — receive the optimized content. If an agent misuses the data, the identity chain enables enforcement.
3. **Billing and metering.** The identity headers enable per-agent, per-provider, or per-owner metering of content delivery. Premium APIs can charge for agent-optimized access. Free-tier access can be rate-limited by identity rather than by IP address (which agents can share or rotate).

**Content discovery via `.well-known/elpis.json`:**

The existing Elpis discovery document (Section 10.4) naturally extends to advertise agent-optimized content delivery:

```json
{
  "elpis_version": "0.1.0",
  "capabilities": ["agent-identity", "header-signing", "xrpl-anchoring", "agent-content"],
  "agent_content": {
    "supported": true,
    "format": "application/elpis+json",
    "scope": ["products", "search", "account"],
    "documentation": "https://example.com/docs/agent-api"
  }
}
```

An agent discovering a domain in the Elpis registry can check the `agent-content` capability before making a request, enabling proactive content negotiation.

**Relationship to existing standards:**

| Standard | Purpose | Elpis Agent Content |
|---|---|---|
| RSS/Atom | Structured content for feed readers | Structured content for AI agents |
| AMP | Optimized pages for mobile | Optimized pages for agents |
| robots.txt | What bots *may* access | What agents *receive* |
| Schema.org | Metadata annotations on HTML | Full content replacement |
| MCP (Anthropic) | Tool interface for LLMs | Action interface on web pages |

The key differentiator is identity-gating: unlike RSS (public), AMP (public), or Schema.org (embedded in public HTML), Elpis agent content is served exclusively to cryptographically identified agents. This transforms website optimization from a public good (benefiting all crawlers including malicious ones) into a trust-gated service (benefiting only accountable agents).

**Deployment model:** The Elpis Gate can be deployed as:
- A **reverse proxy plugin** (Nginx, Caddy, Traefik) — zero application changes
- A **middleware layer** in the web framework (Django, Express, Rails) — deeper integration
- A **CDN edge function** (Cloudflare Workers, AWS Lambda@Edge) — global deployment

In all cases, the existing website continues to serve human visitors unchanged. The agent-optimized content layer is additive, not disruptive.

### 10.7 Security Considerations for Agent-Optimized Content

Section 10.6 introduces a new interaction surface between services and AI agents. This surface creates attack vectors that must be analyzed — not because Elpis introduces them (they exist today in unstructured form), but because a responsible protocol specification must address them explicitly.

#### 10.7.1 Threat Landscape

Four categories of attack are relevant when services deliver structured content to AI agents:

| Attack | Description | Severity |
|---|---|---|
| **Context Pollution** | Service delivers manipulated facts (false prices, misleading descriptions, hidden bias signals) in structured content fields | High |
| **Context Bombing** | Service delivers excessively large payloads (thousands of actions, megabyte-length descriptions) to exhaust the agent's token budget | Medium |
| **Prompt Injection** | Service embeds LLM instructions in content fields (`description`, `actions`) to hijack the agent's behavior | Critical |
| **Social Phishing** | Service designs actions to extract sensitive user data (credentials, payment information, personal data) from the agent | High |

#### 10.7.2 Why Elpis Improves the Status Quo

All four attack vectors exist today — and are strictly worse without Elpis:

**Without Elpis (current state):** An AI agent scraping a website receives an unstructured HTML blob from an anonymous source. The agent has no mechanism to verify the source's identity, no structured channel to validate content, and no recourse if the content is malicious. The attacker is anonymous and untraceable.

**With Elpis:** Every content delivery is cryptographically attributable to a verified service identity on the XRPL. Malicious content triggers flagging, trust score degradation, and potential credential revocation. The structured format enables schema validation *before* content reaches the LLM. Bidirectional identity (Section 10.5) allows the agent to verify the service's trust level before processing content.

The key insight: **Elpis does not eliminate these attacks — it makes them attributable and punishable.** This transforms the game theory: anonymous attacks have zero cost; attacks from a verifiable identity carry reputational, economic, and legal consequences.

#### 10.7.3 Mitigation Architecture

**Schema Validation Layer:** Agent-optimized content responses must conform to a strict JSON schema. Before any content reaches the LLM, a validation layer enforces:
- Maximum payload size (recommended: 10KB for `application/elpis+json` responses)
- Maximum array lengths (e.g., `actions` limited to 20 entries)
- Maximum string lengths per field (e.g., `description` limited to 2000 characters)
- Allowed field names (reject unknown fields that might carry injection payloads)
- Type enforcement (prices must be numbers, URLs must be valid URIs)

Payloads exceeding these limits are rejected with a structured error response, and the violation is logged for potential flagging.

**Data/Instruction Separation:** The most critical mitigation against prompt injection is architectural separation of data and instructions. Content from `elpis+json` responses must be treated as **untrusted data** — never concatenated directly into the LLM prompt. Recommended patterns:
- Place Elpis content in a clearly delimited data section with explicit boundary markers
- Use the LLM's tool/function calling interface to pass structured data rather than embedding it in the conversation
- Apply content sanitization (strip control characters, escape sequences, instruction-like patterns) to all string fields

**Trust-Gated Data Release:** Sensitive user actions (payment, personal data submission) require trust verification of the receiving service:

| Action Type | Required Service Trust Level |
|---|---|
| Navigation, browsing | Any Elpis-identified service |
| Add to cart, wishlist | Trust score > 0.5 |
| Payment, checkout | Trust score > 0.8 + KYC-verified provider |
| Personal data submission | Trust score > 0.9 + KYC-verified + no active flags |

The trust thresholds are configurable by the agent provider and the user, allowing risk-appropriate policies.

**Network-Level Abuse Detection:** The Elpis proxy — which sees all agent-to-service interactions — can detect abuse patterns:
- Repeated large payloads from the same service (context bombing)
- Content that triggers prompt injection detection heuristics
- Services that request disproportionate amounts of user data relative to their stated purpose
- Sudden changes in content structure that deviate from the service's historical pattern

Detected anomalies are reported to the flagging system (Section 4.4), creating a feedback loop: abusive services lose trust, reducing their ability to interact with agents.

#### 10.7.4 Comparison with Unstructured Web Scraping

| Security Property | HTML Scraping (no Elpis) | Elpis Agent Content |
|---|---|---|
| Source verification | None (anonymous) | Cryptographic (XRPL DID) |
| Content validation | Impossible (unstructured) | Schema enforcement (structured JSON) |
| Injection surface | Entire HTML document | Defined, validatable fields |
| Abuse attribution | IP-based (easily spoofed) | Identity-based (cryptographically bound) |
| Abuse consequences | None (anonymous attacker) | Flagging, trust degradation, revocation |
| Data release control | None (agent decides autonomously) | Trust-gated (policy-enforced thresholds) |

The structured nature of Elpis agent content is itself a security advantage: it reduces the attack surface from an arbitrary HTML document (unbounded complexity) to a defined JSON schema (bounded, validatable). This does not eliminate risk, but it transforms the problem from "defend against anything" to "validate against a specification" — a fundamentally more tractable security posture.

#### 10.7.5 False Flagging and Reputation System Abuse

The graduated flagging system (Section 4.4) introduces a meta-attack surface: the flagging mechanism itself can be weaponized. False flagging — the deliberate, malicious reporting of legitimate agents or services — is a well-known problem in reputation systems (review bombing, DMCA abuse, coordinated mass reporting). In the Elpis context, this threat requires specific architectural countermeasures.

**Attack scenarios:**

| Attack | Description | Goal |
|---|---|---|
| **Competitive False Flagging** | Provider A flags agents of competitor Provider B | Destroy competitor's trust score and market access |
| **Coordinated Flag Bombing** | Multiple colluding identities simultaneously flag a legitimate agent | Trigger automatic revocation through volume |
| **Retaliatory Flagging** | Agent is flagged as retaliation for a legitimate report it filed | Discourage honest flagging through fear of counter-reports |
| **Sybil-Assisted Flagging** | Attacker creates many low-cost identities solely for flagging purposes | Amplify flagging volume without real trust investment |

**Mitigation: Skin in the Game**

The core defense against false flagging is ensuring that flagging carries a cost proportional to its impact — the flagger must have "skin in the game":

1. **Weighted Flags**: A flag's impact scales with the reporter's trust score, KYC level, and account age. A flag from a newly created identity with no KYC has near-zero weight. A flag from a long-established, KYC-verified provider carries significant weight. This directly counters Sybil attacks: creating many identities provides no amplification if each identity has negligible trust weight.

2. **Flag Stake**: Filing a flag requires a small XRP reserve lock (analogous to the XRPL's owner reserve mechanism). This reserve is returned if the flag is upheld by review, or forfeited if the flag is determined to be malicious. The economic cost makes bulk false flagging expensive.

3. **Reporter Accountability**: Every flag is itself an on-chain credential — the reporter's identity is permanently and publicly linked to the flag. False flagging therefore creates a permanent, auditable record of abuse by the reporter. Repeated false flags degrade the reporter's own trust score.

4. **Graduated Escalation**: The flagging severity levels (Info, Warning, Critical) require increasing authority thresholds:

| Flag Level | Who Can File | Automatic Effect | Review Required? |
|---|---|---|---|
| Info | Any Elpis-identified entity | Logged, no restriction | No |
| Warning | Trust score > 0.5, KYC basic | Limited capabilities | Optional (auto-expires after 30 days) |
| Critical | Trust score > 0.8, KYC enhanced, OR multi-party consensus | Credential revocation | **Yes** — requires independent review before taking effect |

Critical flags — the only level that triggers revocation — cannot be filed unilaterally by a single entity (unless that entity has exceptionally high trust and KYC). In the general case, critical flags require **multi-party consensus**: at least M-of-N independent reporters must file consistent flags before revocation is triggered. This directly prevents single-actor competitive flagging.

5. **Counter-Flag and Appeal**: A flagged entity can file a counter-flag (appeal) which triggers a review process. During appeal, Warning flags are suspended (capabilities restored pending review). Critical flags remain in effect during appeal — the precautionary principle applies — but the appeal creates an on-chain record that prevents permanent damage from a single false report.

6. **Flag Pattern Analysis**: The network monitors flagging patterns across all participants:
   - Entity that flags disproportionately many competitors → suspicious
   - Cluster of new accounts filing simultaneous flags → coordinated attack
   - Flag immediately following a counter-flag → retaliatory pattern
   - Entity with high flag-filing rate but low upheld rate → serial false flagger

Detected patterns trigger automatic trust score adjustments for the flagging entity, not the flagged entity.

**The anti-Sybil property of Elpis identity is itself the primary defense.** In anonymous reputation systems, Sybil attacks are devastating because creating fake identities is free. In Elpis, every identity requires: (a) a wallet with XRP reserve, (b) a provider certificate from a certified Provider CA, (c) optionally KYC verification. The cost of creating a credible flagging identity — one whose flags carry meaningful weight — is substantial. And each identity's flagging history is permanent and publicly auditable. This makes false flagging a high-cost, high-risk activity with diminishing returns — the opposite of what an attacker needs for systematic abuse.

### 10.8 The Agent Provider Economy: Why Local Agents Strengthen the Case

A natural objection to Elpis is that it requires operator-controlled infrastructure — and therefore cannot cover locally operated AI agents (desktop applications, on-device models, self-hosted LLMs). This appears to be a scope limitation. Upon closer examination, it is the opposite: the existence of unmanaged local agents is precisely what creates the market dynamics that drive Elpis adoption.

#### 10.8.1 The Email Provider Analogy

Consider email. Every individual *can* operate their own mail server. Almost no one does. The reasons are instructive:

1. **Technical complexity**: Configuring DNS (MX, SPF, DKIM, DMARC), TLS certificates, spam filtering, and deliverability monitoring exceeds most users' capabilities.
2. **Reputation bootstrapping**: A new, unknown mail server is treated as spam by default. Building sender reputation takes months of consistent, clean behavior.
3. **Ongoing maintenance**: IP blacklist monitoring, security patching, abuse handling — the operational burden is continuous.
4. **De facto exclusion**: An improperly configured mail server's messages are silently dropped or spam-filtered by major providers. The sender may not even know their messages aren't arriving.

The result: a provider economy emerged (Gmail, Outlook, Fastmail) where specialists handle the infrastructure, and users benefit from shared reputation, compliance, and reliability. Self-hosting remains possible but is a niche activity for experts.

**The same dynamic applies to autonomous AI agents — with an additional regulatory dimension.**

#### 10.8.2 Regulatory Pressure: The EU AI Act as Adoption Catalyst

The EU AI Act (Regulation 2024/1689, effective August 2025) imposes significant obligations on deployers of AI systems, particularly for high-risk applications:

- **Conformity assessments** before deployment
- **Risk management systems** with continuous monitoring
- **Logging and audit trails** for accountability
- **Human oversight** mechanisms
- **Transparency obligations** toward affected persons
- **Incident reporting** to national authorities

An individual operating an autonomous AI agent locally — one that makes API calls, interacts with services, processes personal data, or takes autonomous actions — bears the **full regulatory burden** as the deployer. This includes:

- Conducting a conformity assessment for every agent interaction that falls under high-risk categories
- Maintaining audit logs that satisfy regulatory requirements
- Implementing human oversight mechanisms
- Reporting incidents to the relevant national authority
- Demonstrating compliance upon regulatory inquiry

For a managed provider, these obligations are amortized across thousands of agents and customers. For an individual, they are prohibitive. The regulatory asymmetry creates a natural pull toward providers — not because individuals are forbidden from operating agents, but because the compliance burden makes it impractical.

#### 10.8.3 The Self-Reinforcing Adoption Cycle

The dynamics described above create a self-reinforcing cycle that drives Elpis adoption without requiring mandates:

```
1. EU AI Act makes unmanaged agents legally risky
     ↓
2. Users migrate to providers who handle compliance
     ↓
3. Providers adopt Elpis (infrastructure-level identity = compliance-by-design)
     ↓
4. Services trust Elpis-identified agents (preferential access)
     ↓
5. Unidentified agents lose access (the "spam filter" effect)
     ↓
6. More users choose providers → more providers adopt Elpis → more services validate
     ↓
7. → Back to step 4 (flywheel accelerates)
```

At each step, the incentives are aligned:
- **Users** want reliable agent access without personal liability → choose providers
- **Providers** want differentiation and compliance → adopt Elpis
- **Services** want to distinguish legitimate agents from scrapers/attackers → validate Elpis headers
- **Regulators** want traceable, accountable AI systems → Elpis provides this by default

**The local agent does not need to be prohibited — it is naturally disadvantaged.** An unidentified agent increasingly encounters reduced rate limits, additional verification challenges, CAPTCHA walls, and outright access denial — the same trajectory as an unauthenticated HTTP request in a post-HTTPS world. The individual can still run a local agent, just as they can still run a mail server. But the practical utility diminishes as the identified ecosystem grows.

#### 10.8.4 The Provider as Trust Intermediary

Agent providers serve a function analogous to certificate authorities in the TLS ecosystem or banks in the financial system: they are **trust intermediaries** who vouch for entities that cannot independently establish trust.

An individual user has no reputation in the Elpis network. A provider — with a KYC-verified identity, a track record of well-behaved agents, a certified Provider CA, and economic stake (XRP reserves, brand reputation) — provides the trust bridge. The user's agent inherits the provider's trust floor while building its own interaction history.

This is not a centralization weakness — it is how trust scales in every domain:
- TLS: CAs vouch for websites
- Finance: Banks vouch for account holders
- Email: Providers vouch for senders (DKIM signatures)
- Elpis: Providers vouch for agents

The provider economy is not an obstacle to Elpis adoption. It is the mechanism through which adoption occurs.

### 10.9 Governance and Progressive Decentralization

Section 4.2 describes the Root CA as a multi-signature entity. A natural concern is that during the bootstrap phase, the Root CA is operated by a small number of initial signers — creating a centralization risk. This section addresses the governance model that evolves the Root CA from a bootstrapped trust anchor to a progressively decentralized institution.

#### 10.9.1 The Bootstrap Problem

Every trust system faces the same bootstrap challenge: the first participants must trust each other before the system can generate trust. TLS had the browser vendors' pre-installed CA lists. DNS had the IANA root zone. Bitcoin had Satoshi's genesis block. The XRPL had Ripple's initial Unique Node List (UNL).

Elpis faces the same challenge. The initial Root CA signers must be chosen before any trust metrics exist. This is not a flaw — it is a necessary property of trust system bootstrapping. The question is not "how to avoid bootstrapping" but "how to ensure the bootstrapped system decentralizes over time."

#### 10.9.2 XRPL Permissioned Domains as Architectural Solution

The XRPL's Permissioned Domains feature (XLS-80) provides a ledger-native mechanism that fundamentally changes the Root CA's role:

**Without Permissioned Domains (hierarchical model):**
```
Root CA  →  certifies  →  Provider CA  →  certifies  →  Agent
           (gatekeeper)                  (delegated)
```

The Root CA is a gatekeeper: every provider certification flows through it.

**With Permissioned Domains (federated model):**
```
Root CA  →  admits  →  Provider Domain (autonomous on-chain)
          (registry)        ├── certifies agents autonomously
                            ├── revokes agents autonomously
                            ├── manages flags autonomously
                            └── no Root CA involvement for daily operations
```

The Root CA becomes a registry — analogous to ICANN's role in DNS. It decides *who participates* but not *what participants do within their domain*. A provider with an established Permissioned Domain on the XRPL operates with full autonomy: certifying agents, revoking compromised agents, managing trust scores — all without contacting the Root CA.

This architectural shift has three critical properties:
1. **Operational independence**: Provider outages do not cascade to the Root CA. Root CA unavailability does not prevent providers from operating.
2. **Blast radius containment**: A compromised provider can only damage agents within its own domain. Cross-domain contamination requires Root CA compromise.
3. **Governance simplification**: The Root CA's governance scope is reduced from "all operations" to "admission and exclusion" — a much smaller and more auditable decision space.

#### 10.9.3 Progressive Decentralization Path

The governance model evolves through four phases:

**Phase 1 — Bootstrap (current):**
- 3-5 initial signers with direct trust relationships
- All signers are founding entities with demonstrated commitment
- Admission by unanimous consent
- Focus: establish the technical infrastructure and first provider certifications

**Phase 2 — Early Growth:**
- 8-12 signers including the first independent providers
- Admission by supermajority vote (e.g., 75% of existing signers)
- Candidates must demonstrate: operational track record (minimum 6 months), successful audit (technical and compliance), no active critical flags against their agents
- Probationary period: new signers have reduced voting weight for the first 12 months

**Phase 3 — Established Network:**
- 15-32 signers (XRPL SignerList maximum) spanning multiple jurisdictions, industries, and organizational types
- Anti-dominance rule: maximum 3 signers per provider organization, with weighted voting to prevent single-entity control
- Mandatory periodic re-certification (annual audit)
- Signer removal by supermajority vote for demonstrated misconduct

**Phase 4 — Institutional Maturity:**
- Signer composition includes: commercial providers, academic institutions, standards bodies, and optionally national regulatory authorities (BSI, ANSSI, ENISA)
- Governance framework documented in a public charter
- For scale beyond the 32-signer XRPL limit: layered multi-signature schemes (regional sub-CAs with their own SignerLists) or off-chain governance voting with on-chain anchoring of decisions

#### 10.9.4 Regulatory Authorities as Trust Anchors

A distinctive opportunity for Elpis governance is the potential inclusion of national cybersecurity or AI oversight authorities as Root CA signers. This would create a unique hybrid model:

- **Not state-controlled**: Regulatory authorities would be signers among many, not sole authorities. They cannot unilaterally revoke providers or agents.
- **Regulatory legitimacy**: Their participation signals institutional endorsement of the trust framework.
- **Cross-jurisdictional trust**: A Root CA signed by BSI (Germany), ANSSI (France), and NIST (USA) carries inherent cross-border legitimacy.
- **Precedent**: This mirrors the WebTrust audit model where independent auditors (including government-adjacent bodies) certify CAs.

Inclusion of regulatory signers is optional and additive — the system functions without them, but benefits from their participation when available.

#### 10.9.5 The DNS Parallel

The evolution described above mirrors the governance history of DNS:

| DNS | Elpis |
|---|---|
| IANA (initial, single entity) | Founding signers (bootstrap) |
| ICANN (multi-stakeholder governance) | Root CA with diverse SignerList |
| ccTLDs (national autonomy) | Provider Permissioned Domains |
| Registrars (operational) | Providers (agent management) |
| DNSSEC (cryptographic integrity) | XRPL anchoring (cryptographic integrity) |

DNS began as a centralized system operated by a single person (Jon Postel). Today it is governed by a multi-stakeholder organization with global participation. The path from centralized bootstrap to decentralized governance is well-understood — the challenge is executing it deliberately rather than waiting for crises to force structural changes.

Elpis benefits from designing the decentralization path into the protocol from the beginning, rather than retrofitting governance structures onto an already-entrenched centralized system.

### 10.10 Ledger Independence and the Case for XRPL

Elpis anchors agent identity on the XRP Ledger. This is a deliberate, empirically motivated choice — not an architectural constraint. This section separates the protocol's ledger-specific implementation from its ledger-independent principles, and justifies the selection of XRPL as the anchoring layer.

#### 10.10.1 What Elpis Requires from a Ledger

The identity anchoring layer must provide the following properties:

| Requirement | Purpose |
|---|---|
| Verifiable Credentials (native) | Store agent certificates, flags, compliance status without smart contracts |
| Multi-Purpose Tokens | Per-agent identity tokens with issuance and revocation |
| Multi-Signature accounts | Root CA governance with M-of-N threshold |
| Permissioned Domains | Provider autonomy with domain-scoped operations |
| Fast finality (< 10 seconds) | Revocation must propagate within seconds, not minutes |
| Low transaction cost | Identity operations (certification, flagging) must be economically viable at scale |
| Public verifiability | Any third party can verify an agent's identity without permission |
| Operational track record | Production stability over years, not months |

#### 10.10.2 Why XRPL

At the time of writing, the XRP Ledger is the only distributed ledger technology that satisfies all requirements natively — without smart contract development:

- **Credentials (XLS-70)**: Native on-chain Verifiable Credentials, purpose-built for the use case. No Solidity, no WASM, no contract deployment.
- **Multi-Purpose Tokens (XLS-33)**: Native token issuance with per-holder properties. Agent identity tokens are first-class ledger objects.
- **Permissioned Domains (XLS-80)**: Provider-scoped domains with autonomous credential management — the architectural foundation for decentralized governance (Section 10.9).
- **Multi-Signing**: Native SignerList with weighted quorum, supporting up to 32 signers.
- **3-5 second finality**: Consensus-based (not proof-of-work), deterministic finality. Revocation is globally visible within one ledger close.
- **Negligible transaction costs**: Current reserve requirements and transaction fees make identity operations economically viable even at millions of agents.
- **12+ years of operation**: The XRPL has operated continuously since 2012 with no security breaches, no rollbacks, and no unplanned downtime — a track record unmatched by most distributed ledger networks.
- **Financial sector trust**: XRPL is used in production by financial institutions for cross-border payments, providing institutional credibility that extends to identity use cases.

No alternative DLT known to the authors provides this combination of features without requiring smart contract development. Ethereum and its L2 networks offer programmability but require custom smart contracts for credential management, carry variable and potentially high gas costs, and provide probabilistic rather than deterministic finality. Hyperledger networks are permissioned and lack public verifiability. Sovrin/Indy are purpose-built for identity but have limited adoption and an uncertain operational future.

#### 10.10.3 Architectural Ledger Independence

While the implementation uses XRPL, the Elpis architecture is designed with a clean separation between the identity mechanism and the anchoring layer:

```
Elpis Proxy / Gateway
        │
        ▼
┌─────────────────────┐
│  Credential Store   │  ← Abstract interface
│  (read/write/revoke)│
└────────┬────────────┘
         │
    ┌────┴────┐
    │ Adapter │
    └────┬────┘
         │
    ┌────┴────────┐
    │ XRPL        │  ← Current implementation
    │ (or future  │
    │  alternative)│
    └─────────────┘
```

The Proxy and Gateway components interact with a **Credential Store abstraction**, not with XRPL APIs directly. This store exposes operations: `certify`, `revoke`, `query`, `subscribe` — operations that any suitable DLT could implement. Replacing the XRPL adapter with an adapter for a different ledger is an engineering task (estimated weeks, not months), not an architectural redesign.

This separation is not hypothetical — it is a natural consequence of the caching architecture described in Section 3.6. The proxy already operates against a Redis cache, not against the ledger directly. The ledger is the source of truth, but it is accessed through a synchronization layer that can be retargeted.

#### 10.10.4 The Pragmatic Position

Elpis is committed to XRPL because it is the best available technology for the purpose — not because the protocol requires it architecturally. Should a future DLT emerge that offers equivalent or superior properties, migration is possible without changing the core protocol (proxy, signing, headers, trust model). The identity is in the infrastructure; the ledger is the trust anchor. Trust anchors can be moved — the infrastructure persists.

This is analogous to how TLS certificates can be issued by different CAs without changing the TLS protocol itself. The protocol defines what a certificate must contain; the CA ecosystem determines who issues them. Elpis defines what an identity anchor must provide; the ledger ecosystem determines where it is stored.

---

### 10.11 Adoption Dynamics: Historical Precedent and Convergent Market Forces

A recurring concern with any new infrastructure protocol is the bootstrapping problem: who adopts first when value depends on network effects? This concern, while valid for many technologies, misunderstands how infrastructure protocols actually achieve adoption. The history of internet infrastructure demonstrates that the critical factor is not a single champion but the convergence of technology readiness, market demand, and regulatory pressure.

#### 10.11.1 The HTTPS Precedent

The adoption of HTTPS is frequently mischaracterized as a top-down initiative driven by Google's 2014 "HTTPS everywhere" campaign. In reality, HTTPS adoption followed a pattern of convergent forces:

1. **Technology readiness.** SSL/TLS existed since 1995, but early implementations were computationally expensive, required costly certificates, and imposed measurable latency. By 2010, hardware acceleration (AES-NI), free certificate authorities (Let's Encrypt, launched 2015), and protocol optimizations (TLS 1.2, session resumption, OCSP stapling) had eliminated the practical barriers.

2. **Market demand.** The dot-com boom created a massive e-commerce ecosystem that required encrypted transactions. Users learned to look for the padlock icon. Payment processors mandated HTTPS for card data (PCI DSS). The demand was not created by a single actor — it emerged from the market itself.

3. **Regulatory and competitive pressure.** Google's search ranking signal (2014) and Chrome's "Not Secure" warnings (2017) accelerated adoption, but they did not initiate it. They pushed an already-moving trend past the tipping point. The EU's GDPR (2018) further cemented the expectation that data in transit must be encrypted.

4. **Self-reinforcing adoption.** Once a critical mass of sites adopted HTTPS, the remaining sites faced increasing competitive and reputational pressure. The cost of *not* adopting exceeded the cost of adoption.

The key insight: HTTPS succeeded not because Google "made it happen," but because it was the right technology at the right moment in history. Google accelerated an inevitable convergence.

#### 10.11.2 The AI Identity Parallel

Elpis stands at a remarkably similar convergence point:

1. **Technology readiness.** The components exist: transparent proxies are battle-tested infrastructure, Ed25519 signing is computationally trivial, container orchestration provides natural isolation boundaries, and the XRPL offers a production-ready public ledger with sub-second finality. Unlike HTTPS in 1995, Elpis does not require waiting for hardware to catch up — the infrastructure is already capable.

2. **Market demand.** The autonomous agent economy is growing exponentially. Every major AI provider — Anthropic, OpenAI, Google, Meta, xAI — is shipping agent capabilities. Multi-agent systems are moving from research prototypes to production deployments. The question "who is this agent and who is responsible for it?" is no longer theoretical — it is a daily operational concern for every organization deploying agents.

3. **Regulatory pressure.** The EU AI Act (effective August 2025) explicitly requires transparency obligations for AI systems, including identification of AI-generated content and accountability chains. The AI Act does not prescribe *how* identity must be established, but it mandates *that* it must be. Elpis provides a compliance-ready answer to a regulatory question that currently has no standardized solution.

4. **Competitive dynamics.** Agent providers who can demonstrate verifiable identity, accountability, and compliance have a competitive advantage. Early Elpis adoption provides a tangible trust differentiator — analogous to early HTTPS adoption signaling "this site takes security seriously."

#### 10.11.3 Who Is the "Chrome" for Elpis?

The question "who will push Elpis adoption?" assumes the HTTPS model requires a single dominant player. But the actual HTTPS adoption story involved multiple actors with aligned incentives:

- **Browser vendors** (Chrome, Firefox, Safari) implemented warnings for non-HTTPS sites
- **Certificate authorities** (Let's Encrypt) eliminated cost barriers
- **Hosting providers** (Cloudflare, AWS) made HTTPS the default configuration
- **Regulators** (EU, PCI Council) mandated encryption for specific use cases

For Elpis, the equivalent actors are already identifiable:

- **Cloud providers** (AWS, Azure, GCP) already manage agent execution environments and could integrate Elpis proxies as a managed service — just as they integrated TLS termination
- **AI providers** (Anthropic, OpenAI, Google) have direct incentive to distinguish their agents from unmanaged ones, especially under regulatory pressure
- **Agent platforms** (LangChain, CrewAI, AutoGen) could embed Elpis identity as a standard feature, lowering adoption barriers
- **Regulators** (EU AI Office, national DPAs) will increasingly demand the kind of accountability that Elpis provides

The question is not whether a "Chrome moment" will occur, but which actor will recognize the strategic advantage first. History suggests it will not be a single actor but a cascade: one early mover creates competitive pressure that triggers rapid adoption by peers.

#### 10.11.4 Why This Is Not an Existential Risk

The chicken-and-egg concern assumes that Elpis requires universal adoption to provide value. This is incorrect for two reasons:

**First**, Elpis provides immediate value to individual adopters. An agent provider deploying Elpis gains verifiable identity for compliance, a trust differentiator for customers, and an audit trail for incident response — regardless of whether any other provider has adopted the protocol. The value is not purely network-dependent.

**Second**, Elpis is designed for incremental adoption. The `/.well-known/elpis.json` discovery mechanism allows web services to optionally recognize Elpis-identified agents without requiring adoption themselves. A web service can simply check for X-Elpis-* headers and log them — providing observability into agent traffic — with zero changes to its application logic. The barrier to "passive adoption" (recognizing Elpis identities) is near zero.

The adoption curve is therefore not a cliff (requiring critical mass before any value emerges) but a ramp (providing increasing value with each additional participant). This is the same pattern that made HTTPS adoption self-sustaining once it passed approximately 50% of web traffic — a threshold reached not through mandate but through accumulated individual decisions.

The historical pattern is clear: infrastructure protocols succeed when technology readiness, market demand, and regulatory pressure converge. For AI agent identity, all three forces are converging now. The question is not *whether* a standardized agent identity protocol will be adopted, but *which one* — and Elpis is, at the time of writing, the only candidate that operates at the infrastructure level where identity cannot be circumvented by the agent itself.

---

### 10.12 Proxy Scaling and Protocol Evolution: From Interception to Native Integration

A legitimate engineering concern with the current Elpis architecture is the computational cost of TLS interception (SSL Bump). Every HTTPS request from an agent requires the proxy to terminate the TLS session, inject identity headers, and re-establish a new TLS session to the destination — effectively doubling the cryptographic overhead per request. At scale, this represents a non-trivial CPU and latency burden.

This concern is real but mischaracterizes the nature of the problem. SSL Bump is the *current implementation mechanism*, not an architectural requirement. The Elpis architecture requires exactly one thing: that cryptographic identity headers are present in every outgoing HTTP request from an agent's execution environment. How those headers arrive in the request is an implementation detail — and one with a clear evolutionary path.

#### 10.12.1 The Performance Objection in Historical Context

Every major infrastructure protocol has faced the same objection at inception:

- **HTTPS (1995):** "SSL handshakes are too expensive for every connection." Today, TLS 1.3 completes a handshake in a single round-trip (0-RTT for resumed sessions), hardware AES-NI instructions make encryption effectively free, and HTTPS is the default for all web traffic. The "performance problem" was solved by hardware evolution, protocol optimization, and dedicated silicon.

- **DNS over HTTPS (2018):** "Encrypting every DNS query adds unacceptable latency." Today, DoH is a standard browser feature with negligible performance impact, enabled by persistent connections and connection pooling.

- **mTLS in service meshes (2017):** "Mutual TLS between every microservice is too expensive." Today, Istio and Linkerd handle mTLS transparently for millions of production services, optimized through connection pooling, certificate caching, and eBPF-accelerated data paths.

The pattern is consistent: performance objections to security infrastructure are valid at launch and irrelevant within 5-10 years. The computational cost of Ed25519 signature generation (Elpis's core operation) is approximately 50 microseconds — orders of magnitude cheaper than the TLS operations it currently piggybacks on.

#### 10.12.2 Near-Term Optimizations

Even within the current SSL Bump architecture, significant optimizations are available:

1. **Connection pooling and session resumption.** The proxy can maintain persistent TLS sessions to frequently accessed destinations, amortizing handshake costs across multiple requests. TLS 1.3 session tickets reduce resumed handshakes to near-zero overhead.

2. **Selective interception.** Not every destination requires identity injection. The proxy can maintain an allowlist of Elpis-aware services (discoverable via `/.well-known/elpis.json`) and pass through traffic to non-Elpis destinations without interception. This reduces SSL Bump operations to only those requests where identity will actually be verified.

3. **Hardware acceleration.** Modern server CPUs include AES-NI and AVX-512 instructions that make TLS operations nearly free. Dedicated TLS offload hardware (SmartNICs, DPUs) can handle interception entirely in the network path, removing CPU overhead from the proxy process.

4. **Horizontal scaling.** The proxy is stateless — agent identity is derived from runtime metadata and cached credentials, not from proxy-local state. Multiple proxy instances can serve the same agent pool behind a load balancer with no coordination overhead.

#### 10.12.3 The Evolutionary Path: Protocol-Native Identity

The deeper answer to the scaling concern is that SSL Bump is a transitional mechanism. The Elpis header schema (X-Elpis-*) is designed to be transport-agnostic — the headers are standard HTTP headers that can be injected by any mechanism, not only TLS interception. Several evolutionary paths lead to native integration:

**TLS Extensions.** The TLS protocol supports custom extensions (RFC 8446, Section 4.2). An Elpis TLS extension could carry agent identity information directly in the TLS handshake, making it available to the server before the first HTTP byte is sent — without requiring interception. This is analogous to Server Name Indication (SNI), which was added to TLS to solve a similar "how do we convey metadata about the client before the application layer" problem.

**HTTP/3 and QUIC.** HTTP/3's QUIC transport provides a natural injection point. QUIC's connection-level metadata and early data mechanisms could carry Elpis identity as part of the transport setup, eliminating the need for header injection entirely. The proxy would participate in the QUIC handshake rather than intercepting TLS.

**Proxy Protocol extensions.** HAProxy's Proxy Protocol (v2) already carries connection metadata (source IP, TLS parameters) through proxy chains. A Proxy Protocol v3 or custom TLV extension could carry Elpis identity fields, allowing standard reverse proxies and load balancers to propagate agent identity without application-layer modification.

**IETF standardization.** The X-Elpis-* headers could evolve into an IETF RFC — similar to how X-Forwarded-For became the standardized Forwarded header (RFC 7239). A standardized Agent-Identity header would allow web servers, CDNs, and API gateways to natively recognize agent identity without any Elpis-specific integration.

#### 10.12.4 The Symbiosis Model

The most likely evolution is not replacement but symbiosis: Elpis identity injection coexists with and gradually migrates into native protocol support.

**Phase 1 — Proxy injection (current).** SSL Bump provides universal coverage with no changes required to agents, servers, or protocols. This is the bootstrap mechanism — it works today with existing infrastructure.

**Phase 2 — Hybrid.** Elpis-aware HTTP libraries and agent frameworks natively inject X-Elpis-* headers, eliminating the need for TLS interception for cooperative agents. The proxy continues to serve as a fallback for unmodified agents, ensuring the "infrastructure-level" guarantee is maintained. This phase is analogous to the period when both HTTP and HTTPS coexisted, with gradual migration.

**Phase 3 — Protocol-native.** TLS extensions or HTTP/3 metadata carry agent identity as a standard protocol feature. The proxy's role shifts from active interception to passive verification — confirming that the identity claimed by the agent matches the identity expected from its runtime environment. This is the "TLS certificate" endgame: identity is part of the protocol, not bolted on.

**Phase 4 — Infrastructure default.** Cloud providers, container orchestrators, and serverless platforms include agent identity as a built-in feature — just as they include TLS termination today. The proxy becomes invisible, absorbed into the platform's network stack.

This evolution does not require any changes to the Elpis core architecture. The trust model (CA hierarchy, XRPL anchoring, credential verification) remains identical regardless of whether identity is injected by a proxy, by an HTTP library, by a TLS extension, or by the platform itself. The *what* (cryptographic agent identity in every request) is permanent; the *how* (injection mechanism) evolves with the protocol landscape.

The concern about proxy scaling is therefore not a limitation of the Elpis architecture but a snapshot of its current implementation — an implementation that already has a clear optimization path and a natural evolution toward protocol-native integration. The history of internet infrastructure consistently shows that today's performance concern becomes tomorrow's solved problem.

---

### 10.13 Privacy and the Supercookie Problem: From Persistent Identity to Selective Disclosure

The most ethically significant concern with the Elpis architecture is also the most fundamental: every outgoing request from an agent carries the same cryptographic identity. An agent visiting Service A and then Service B presents the same X-Elpis-Agent-DID, the same signature chain, the same provider identity. This is, by design, a persistent cross-site identifier — a "supercookie" that cannot be cleared, rotated on demand, or blocked by the agent.

This is not a bug. It is the core feature. And it creates a genuine tension between accountability (the protocol's primary goal) and privacy (an equally legitimate concern). This section addresses that tension directly.

#### 10.13.1 The Ethical Dimension

The supercookie analogy is apt and must not be dismissed. In the human web, persistent cross-site identifiers enable:

- **Behavioral profiling.** Services can correlate an agent's activity across unrelated contexts, building comprehensive behavioral profiles.
- **Discrimination.** Services could treat agents differently based on their identity history — refusing service, offering degraded content, or applying differential pricing.
- **Surveillance.** A sufficiently connected set of services could reconstruct a complete activity log for any identified agent.

These are the same concerns that led to GDPR, ePrivacy regulations, and the browser ecosystem's multi-year effort to eliminate third-party cookies. Introducing a new persistent identifier — even for non-human actors — requires careful consideration.

However, the framing "agents deserve the same privacy as humans" conflates two fundamentally different contexts.

#### 10.13.2 Agent Privacy vs. Human Privacy: A Different Threat Model

Human privacy protections exist because:
1. Humans have an inherent right to autonomy and self-determination
2. Humans cannot meaningfully consent to tracking at the scale it occurs
3. The power asymmetry between individuals and corporations is extreme
4. Profiling can lead to real-world harm (discrimination, manipulation, persecution)

Agent privacy operates in a different threat model:
1. Agents act on behalf of an operator who has legal responsibility for their actions
2. The operator explicitly configures the agent's identity — consent is institutional, not individual
3. The power relationship is between organizations (agent operator vs. service provider), not between an individual and a corporation
4. The primary risk of agent anonymity is not privacy but accountability evasion

This does not mean agent privacy is irrelevant. It means the privacy requirements are different: the question is not "should the agent be anonymous?" (generally no — the EU AI Act explicitly requires AI identification) but "how much identity information should be revealed in each interaction?"

#### 10.13.3 Selective Disclosure: The Graduated Response

The solution is not less identity but *smarter* identity. The W3C Verifiable Credentials specification (which Elpis already builds on via XRPL Credentials) natively supports **Selective Disclosure** — the ability for a credential holder to reveal specific claims without exposing the entire credential.

Applied to Elpis, this enables graduated disclosure levels:

**Level 0 — Full transparency (current default).** All X-Elpis-* headers are present. The receiving service knows the agent's DID, provider, operator, and can verify the full trust chain. Appropriate for: high-trust interactions, regulated environments, financial transactions.

**Level 1 — Provider-only.** The agent proves it is operated by a verified Elpis provider without revealing its specific identity. The service knows "this is a managed, accountable agent" but not "this is Agent X owned by Company Y." Appropriate for: general web browsing, information retrieval, low-sensitivity interactions.

**Level 2 — Category proof.** The agent proves a specific attribute (e.g., "I am authorized for financial data access" or "I am EU AI Act compliant") without revealing identity. Implemented via W3C Verifiable Presentations with selective attribute disclosure. Appropriate for: access control decisions that depend on capability rather than identity.

**Level 3 — Zero-knowledge existence proof.** The agent proves it possesses a valid Elpis credential without revealing *any* identifying information. The service knows only: "this request comes from a cryptographically verified agent in the Elpis ecosystem." This is the strongest privacy guarantee compatible with accountability.

Levels 0-2 are implementable today using standard W3C Verifiable Presentation mechanisms. Level 3 requires zero-knowledge proof infrastructure.

#### 10.13.4 XRPL Confidential Transfers: The Zero-Knowledge Path

The XRP Ledger's roadmap includes Confidential Transfers — zero-knowledge proof-based encryption of transaction amounts and balances for Multi-Purpose Tokens (MPTs), scheduled for activation in Q1 2026. This feature, designed for institutional privacy on the Permissioned DEX, provides the cryptographic foundation for Level 3 privacy in Elpis:

**ZK-Proof of Credential Validity.** An agent can generate a zero-knowledge proof that it holds a valid, non-revoked Elpis credential anchored on the XRPL — without revealing which credential, which agent DID, or which provider issued it. The verifier learns exactly one bit of information: "this agent is part of the Elpis trust network."

**ZK-Proof of Attribute Possession.** Using the same ZK infrastructure, an agent can prove it possesses specific credential attributes (e.g., "admin-seer role," "EU jurisdiction," "financial-data-authorized") without revealing the credential itself. This extends Selective Disclosure from cryptographic signatures to full zero-knowledge proofs.

**Confidential Agent Transactions.** When agents interact with each other via on-chain operations (credential exchanges, flag submissions, trust score queries), Confidential Transfers ensure these interactions are private — preventing the "who talks to whom" metadata leakage that is often more revealing than content.

The integration path is direct: Elpis already anchors credentials as XRPL MPTs. When Confidential Transfers become available for MPTs, the same credentials can be verified via ZK proofs without modification to the credential schema — only the verification method changes.

#### 10.13.5 Architectural Integration: The Privacy Proxy Extension

The Elpis proxy architecture naturally accommodates privacy levels. The proxy already controls which headers are injected into outgoing requests. Extending this to support disclosure levels requires:

1. **Policy configuration.** The agent operator defines a disclosure policy: which privacy level to use for which destination categories. This can be rule-based (e.g., "Level 0 for financial services, Level 1 for general web, Level 2 for data providers") or dynamic (negotiated per-request via the `/.well-known/elpis.json` discovery mechanism).

2. **Verifiable Presentation generation.** For Levels 1-2, the proxy generates W3C Verifiable Presentations from the agent's full credential, disclosing only the attributes required by the destination's policy. This is a standard VP operation, not an Elpis-specific extension.

3. **ZK proof generation.** For Level 3, the proxy generates zero-knowledge proofs using the XRPL Confidential Transfer infrastructure. The proof is injected as a compact header (replacing the full X-Elpis-* header set with a single ZK proof blob).

4. **Destination-driven negotiation.** The `/.well-known/elpis.json` endpoint is extended to include a `requiredDisclosureLevel` field, allowing services to specify the minimum identity information they require. An agent visiting a service that requires only Level 1 automatically reduces its disclosure — even if its default is Level 0.

#### 10.13.6 The Privacy Spectrum as Strength

The supercookie concern, properly addressed, transforms from a weakness into a differentiator. No other agent identity proposal offers graduated privacy:

- **API key authentication:** Binary — either you reveal your full identity or you have no access. No middle ground.
- **OAuth tokens:** Scoped by permission, not by identity disclosure. The token reveals which application, not which level of identity.
- **mTLS client certificates:** Full certificate or nothing. No selective disclosure.

Elpis with Selective Disclosure offers a spectrum: from full transparency (when accountability requires it) to zero-knowledge existence proofs (when privacy requires it), with graduated levels in between — all anchored in the same trust infrastructure.

This is the correct architectural response to the privacy concern: not "agents should be anonymous" (which undermines the entire accountability model) and not "agents must always be fully identified" (which creates the supercookie problem), but "the level of identity disclosure should match the requirements of the interaction." The protocol provides the full spectrum; the operator and the service negotiate the appropriate level.

---

### 10.14 Proxy Confidentiality: The TLS Interception Trust Model

A frequently raised concern is that the Elpis proxy, by performing TLS interception (SSL Bump), can read all plaintext HTTP traffic — including credentials, API keys, session tokens, and sensitive request/response payloads. This concern is legitimate and must be addressed directly.

#### 10.14.1 The Technical Reality

Yes, the Elpis proxy in SSL Bump mode has access to plaintext HTTP traffic. This is inherent to TLS interception — the proxy terminates the agent's TLS session, reads the HTTP layer to inject X-Elpis-* headers, and establishes a new TLS session to the destination. During this process, the proxy can observe all request and response content.

This is not a design flaw. It is a necessary consequence of infrastructure-level identity injection via header manipulation. The proxy must access the HTTP layer to add headers — there is no mechanism in TLS to inject HTTP headers without terminating the TLS session.

#### 10.14.2 Why This Is Not a New Trust Boundary

The critical insight is that the proxy is operated by the **same entity** that operates the agent. The provider who runs the agent's container also runs the Elpis proxy. This means:

1. **The provider already has full access to the agent's environment.** Environment variables (which commonly contain API keys), configuration files, mounted secrets, and filesystem contents are all accessible to the provider. The proxy does not grant access to information the provider could not already obtain.

2. **The provider can already inspect agent traffic through other means.** Container runtime logging, network namespace inspection, tcpdump on the host network interface — any operator with root access to the host can capture and decrypt agent traffic regardless of whether an Elpis proxy is present.

3. **No third party gains access.** The proxy is not a separate service operated by a different organization. It is infrastructure co-located with the agent, under the same administrative domain. The trust boundary between agent and proxy is identical to the trust boundary between agent and host — which already exists and is already accepted.

This trust model is identical to universally accepted infrastructure patterns:

| Infrastructure Component | Sees Plaintext? | Trust Model |
|---|---|---|
| Cloud Load Balancer (AWS ALB, GCP LB) | Yes (TLS termination) | Provider-operated |
| CDN (Cloudflare, Akamai, Fastly) | Yes (TLS termination) | Third-party trusted |
| API Gateway (Kong, Apigee) | Yes (TLS termination) | Provider-operated |
| Corporate Forward Proxy (Zscaler, BlueCoat) | Yes (SSL inspection) | Employer-operated |
| Service Mesh Sidecar (Istio/Envoy) | Yes (mTLS termination) | Platform-operated |
| **Elpis Proxy** | **Yes (SSL Bump)** | **Provider-operated** |

Every entry in this table sees plaintext traffic. None is considered an unacceptable security risk in production deployments, because the trust model is understood: the operator of the infrastructure is trusted with the data that transits it.

#### 10.14.3 Data Minimization in Practice

While the proxy has access to plaintext traffic, the Elpis protocol requires it to process only the following data for identity injection:

- **HTTP method** (e.g., GET, POST)
- **Request URL** (including query parameters)
- **SHA-256 hash of the request body** (not the body itself for signing purposes, though the body transits the proxy)
- **Timestamp and nonce** (generated by the proxy)

The proxy does not need to store, log, or transmit request/response payloads. A minimal implementation reads the HTTP stream, computes the canonical string, signs it, injects headers, and forwards the request — without persisting any payload data. Audit logs record connection metadata (source DID, destination host, timestamp, response status) but not request content.

Operators concerned about data exposure can implement additional safeguards:

1. **Memory-only processing.** The proxy processes requests in streaming mode without writing payloads to disk.
2. **Audit log scope configuration.** Operators can configure which metadata is logged, excluding URL query parameters or response headers that might contain sensitive data.
3. **TEE-isolated proxy.** As described in Section 6.2.1, running the proxy inside a Trusted Execution Environment (SGX/Nitro Enclave) ensures that even the host operator cannot inspect the proxy's memory during TLS processing — providing confidentiality guarantees beyond what any of the comparable infrastructure components in the table above offer.

#### 10.14.4 The Evolutionary Resolution

The SSL Bump trust model is a property of the current implementation phase (Phase 1 in Section 10.12.4), not an architectural constant. As the protocol evolves:

- **Phase 2 (Hybrid):** Agent-side HTTP libraries inject X-Elpis-* headers natively. The proxy no longer performs TLS interception — it only verifies that the correct headers are present (pass-through TLS with header validation on non-encrypted metadata). The proxy sees only encrypted traffic.

- **Phase 3 (Protocol-native):** Identity is carried in TLS extensions or QUIC transport metadata. No HTTP-layer interception occurs at all.

- **Phase 4 (Infrastructure default):** Identity injection is handled by the container runtime or cloud platform's network stack, analogous to how TLS termination is handled by cloud load balancers today.

In each successive phase, the proxy's access to plaintext traffic decreases — from full visibility (Phase 1) to zero visibility (Phase 4). The trust model becomes progressively less dependent on operator trustworthiness as the protocol matures.

#### 10.14.5 The Honest Position

It would be intellectually dishonest to claim that TLS interception raises no confidentiality concerns. It does. The Elpis position is:

1. The concern is real but not unique — it applies to every TLS-terminating infrastructure component in production today.
2. The trust model is explicit: the agent provider is trusted with agent traffic because they already have full access to the agent's execution environment.
3. Data minimization practices reduce exposure in the current implementation.
4. TEE deployment (Section 6.2.1) provides hardware-enforced confidentiality beyond what competing infrastructure offers.
5. The protocol's evolution toward native integration (Section 10.12) progressively eliminates the need for TLS interception entirely.

The question is not "does the proxy see plaintext?" (yes, like all TLS-terminating infrastructure) but "does the proxy create a new trust boundary that did not previously exist?" (no — the provider already controls the agent's environment).

#### 10.14.6 The Provider as High-Value Target

Making the provider the explicit trust anchor has a corollary: the provider becomes the highest-value attack target in the Elpis ecosystem. Compromising a provider means gaining access to signing keys, plaintext traffic, and the ability to impersonate or frame any agent under that provider's control. This is a serious concern — and it is the same concern that applies to every centralized trust infrastructure in production today.

**The pattern is universal:**

| Trust Infrastructure | What Compromise Yields | Mitigation Ecosystem |
|---|---|---|
| Certificate Authority (DigiCert, Let's Encrypt) | Ability to issue fraudulent TLS certificates for any domain | CT logs, CAA records, key ceremonies, HSMs, audits |
| Cloud Provider (AWS, GCP, Azure) | Access to all customer workloads, data, and credentials | SOC 2, ISO 27001, hardware isolation, shared responsibility model |
| Email Provider (Google, Microsoft) | Access to all email content, password resets, 2FA bypass | Encryption at rest, access controls, transparency reports |
| DNS Provider (Cloudflare, Route53) | Ability to redirect any domain to attacker-controlled servers | DNSSEC, monitoring, registry locks |
| **Elpis Provider** | **Signing keys, agent traffic, identity impersonation** | **See mitigations below** |

The existence of high-value targets does not make these systems unviable — it makes security investment proportional to the stakes. The mitigation strategy for Elpis providers follows the same patterns that have proven effective for other trust infrastructure:

**Technical mitigations (already specified in this paper):**

1. **Hardware-backed key management (Section 6.2.1).** TEE/HSM deployment ensures signing keys cannot be extracted even with full host compromise. This is a strictly stronger guarantee than what most Certificate Authorities provide for their intermediate signing keys.

2. **On-chain audit trail.** Every agent certificate issuance, revocation, and flag is recorded on the XRPL — publicly visible and immutable. A compromised provider cannot silently issue fraudulent certificates; any issuance is immediately visible to the entire ecosystem.

3. **Multi-signature governance (Section 10.9).** Root CA operations require multiple signers. A single compromised key holder cannot unilaterally issue provider certificates or revoke legitimate ones.

4. **Bidirectional flagging (Section 4.4).** If a provider's agents behave anomalously (indicating compromise), any participant in the ecosystem can flag the provider. Flags are on-chain and trigger escalation — creating a distributed early warning system.

5. **Revocation propagation in seconds (Section 4.3).** When a compromise is detected, the provider's certificate can be revoked on-chain in 3-5 seconds, instantly invalidating all agent identities under that provider. Compare this to the days-to-weeks CRL propagation delay in traditional PKI.

**Economic and regulatory mitigations:**

6. **EU AI Act liability.** Providers are legally liable for their agents' actions. This creates a direct financial incentive for security investment that scales with the provider's exposure. Negligent security practices result in regulatory penalties, not just reputational damage.

7. **Market pressure (Section 10.8).** The provider economy creates competitive pressure for security. Providers who suffer breaches lose customers to competitors. This is the same market dynamic that drives cloud providers to invest billions in security infrastructure.

8. **Insurance and audit requirements.** As the provider economy matures, insurance carriers and enterprise customers will require security audits (SOC 2, ISO 27001 equivalents) as a precondition for doing business — the same pattern that professionalized cloud provider security.

**The architectural advantage:**

Critically, Elpis's trust model makes the provider a *visible* high-value target — which is preferable to the alternative. In systems without explicit trust anchors (e.g., unmanaged AI agents using stolen API keys), the attack surface is diffuse, responsibility is unclear, and compromise detection is difficult. By concentrating trust in an identifiable, auditable, regulatable entity, Elpis enables the same security professionalization that transformed cloud computing from "trusting someone else's computer" to an industry with rigorous security standards.

The provider is Target #1 — and that is exactly why the mitigations described above exist. The goal is not to eliminate the target (which would require eliminating centralized trust entirely — an unsolved problem) but to make the target hardened, auditable, and recoverable.

---

## 11. Conclusion

Elpis represents a fundamental shift in how AI agent identity is established: from software-level mechanisms that depend on agent cooperation, to infrastructure-level mechanisms that operate independently of the agent's awareness or consent. The architecture is agnostic to the specific isolation technology: the fundamental principle---that the operator controls the network path between the agent and the internet---holds for containers, virtual machines, serverless functions, and any managed execution environment. By leveraging the transparent proxy pattern, immutable runtime metadata, Ed25519 cryptographic signing, and XRP Ledger anchoring, Elpis provides a comprehensive, LLM-agnostic, prompt-injection-resistant identity framework for autonomous AI agents.

The system has been implemented, deployed, and validated in a production environment. A live reference implementation is publicly accessible at `https://elpis.efiniti.ai`, where the protocol's discovery endpoint (`/.well-known/elpis.json`) and verification endpoint (`/api/whoami`) demonstrate the complete identity flow. An AI agent visiting any web service is automatically identified through cryptographic headers — without login, without cookies, without API keys — purely through its infrastructure-level identity. The `/api/whoami` endpoint serves as both a debugging tool for agent operators and a public proof of concept: any HTTP client sending X-Elpis-* headers receives a JSON response confirming the parsed identity fields.

The approach provides a standardized, infrastructure-level identity mechanism for AI agents that is comparable in architectural significance to TLS certificates for web servers: transparent to the application layer, enforced at the infrastructure layer, and universally applicable regardless of the underlying AI model or framework. Just as every web server today presents a TLS certificate without the application being aware of it, every AI agent operating behind an Elpis proxy presents a cryptographic identity without the model being aware of it.

---

## Appendix A: Protocol Specification Summary

### A.1 Header Format

```
X-Elpis-DID: did:xrpl:{owner_address}#{agent_id}
X-Elpis-Signature: base64(Ed25519_Sign(private_key, canonical_string))
X-Elpis-Timestamp: {ISO 8601 with timezone}
X-Elpis-Nonce: {UUID v4}
X-Elpis-Cert-Hash: sha256:{hex-encoded certificate hash}
X-Elpis-Domain: {provider_domain}.elpis
X-Elpis-Display-Name: {optional human-readable agent name}
X-Elpis-Scope: {optional scope identifier}
X-Elpis-Chain: {optional Base64-encoded certificate chain}
```

### A.2 Canonical String Format

```
{HTTP_METHOD}\n{FULL_URL}\n{SHA256_HEX(BODY)}\n{TIMESTAMP}\n{NONCE}
```

### A.3 DID Format

```
did:xrpl:{XRPL_OWNER_ADDRESS}#{AGENT_ID}
```

Where `AGENT_ID` is an opaque provider-generated identifier (e.g., UUID v4 short form: `a7f3b2c1`). The identifier deliberately does not encode the agent's human-readable name to preserve operational privacy. Providers manage an internal mapping between agent identifiers and display names.

### A.4 Runtime Metadata Schema

The following metadata keys must be set as immutable properties of the agent's execution environment. The syntax varies by runtime; Docker label syntax is shown as reference:

```
pandora.agent.name: {UUID string}         # Opaque agent identifier (UUID)
pandora.agent.did: {DID string}           # W3C DID
pandora.agent.provider: {string}          # Provider domain
pandora.agent.cert-hash: {string}         # SHA-256 of current certificate
pandora.agent.display-name: {string}      # Optional: public-facing agent name
```

**Runtime equivalents:** Docker labels, Podman labels (OCI-compatible), Kubernetes pod annotations, LXC configuration properties (`lxc.custom.*`), containerd labels.

---

## Appendix B: Comparison with Existing Approaches

| Aspect | API Keys | OAuth 2.0 | SPIFFE/SPIRE | Elpis |
|---|---|---|---|---|
| Identity verification | None | Token-based | Certificate-based | Signature-based + DID |
| Agent cooperation required | Yes | Yes | Yes | **No** |
| LLM-agnostic | N/A | N/A | N/A | **Yes** |
| Prompt injection resistant | No | No | N/A | **Yes** |
| Publicly verifiable | No | No | No | **Yes (XRPL)** |
| Instant revocation | Provider-specific | Provider-specific | CA-specific | **On-chain (~5s)** |
| Cross-organizational | No | Limited | Limited | **Yes** |
| Zero agent code changes | No | No | No | **Yes** |

---

## References

1. EU AI Act — Regulation (EU) 2024/1689 of the European Parliament
2. W3C DID Core v1.0 — https://www.w3.org/TR/did-core/
3. W3C Verifiable Credentials Data Model v2.0 — https://www.w3.org/TR/vc-data-model-2.0/
4. RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)
5. RFC 8705 — OAuth 2.0 Mutual-TLS Client Authentication
6. XRPL Documentation — Multi-Purpose Tokens (XLS-33), Credentials (XLS-70), Permissioned Domains (XLS-80) — https://xrpl.org/docs/
7. CrowdStrike Global Threat Report 2025
8. IBM X-Force Threat Intelligence Index 2025
9. SPIFFE — Secure Production Identity Framework for Everyone, SPIFFE Specification v1.0 — https://spiffe.io/docs/latest/spiffe-about/overview/
10. HashiCorp Vault — Secrets Management and Identity-Based Access — https://www.vaultproject.io/
11. Anthropic — "Core Views on AI Safety" (2023); OpenAI — "Our Approach to AI Safety" (2023)
12. Google BeyondCorp — "A New Approach to Enterprise Security", Ward & Beyer, ;login: USENIX, 2014
13. NIST SP 800-207 — "Zero Trust Architecture", Rose et al., August 2020
14. W3C AI Agent Protocol Community Group — https://www.w3.org/community/ai-agent-protocol/ (established May 2025)
15. Sogomonian — "Artificial Intelligence Identity Protocol (AIIP)", Internet-Draft, September 2025 — Note: Independent work on a conceptually different approach (software-level identity); no technical overlap with Elpis' infrastructure-level approach
16. Anthropic — Model Context Protocol (MCP) Specification — https://modelcontextprotocol.io/
17. Docker — Container Security Best Practices, Docker Documentation — https://docs.docker.com/engine/security/
18. RFC 7519 — JSON Web Token (JWT)
19. OAuth 2.0 Authorization Framework — RFC 6749
20. XRPL Multi-Signing — https://xrpl.org/docs/concepts/accounts/multi-signing/

---

*Date of first publication: March 2, 2026. Last revised: March 5, 2026.*
*Reference implementation: https://elpis.efiniti.ai*
