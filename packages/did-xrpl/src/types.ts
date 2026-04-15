/**
 * Types for the did:xrpl DID method.
 *
 * Implements the W3C DID Core v1.0 specification applied to the
 * XRP Ledger as the verifiable data registry.
 *
 * DID format:  did:xrpl:{network}:{address}#{fragment}
 *
 * @see https://www.w3.org/TR/did-core/
 */

// ---------------------------------------------------------------------------
// DID identifiers
// ---------------------------------------------------------------------------

/** Supported XRPL networks. */
export type XRPLNetwork = "mainnet" | "testnet" | "devnet";

/** A fully-qualified did:xrpl identifier. */
export interface XRPLDID {
  /** The full DID string, e.g. `did:xrpl:testnet:rXXX#alice`. */
  did: string;
  /** Network segment. */
  network: XRPLNetwork;
  /** Classic XRPL r-address (owner). */
  address: string;
  /** Optional fragment identifying a specific subject (e.g. agent name). */
  fragment?: string;
}

// ---------------------------------------------------------------------------
// W3C DID Document
// ---------------------------------------------------------------------------

/** Ed25519 verification method (Ed25519VerificationKey2020). */
export interface VerificationMethod {
  id: string;
  type: "Ed25519VerificationKey2020";
  controller: string;
  /** Multibase-encoded public key (z-prefix, base58btc). */
  publicKeyMultibase: string;
}

/** Service endpoint entry. */
export interface ServiceEndpoint {
  id: string;
  type: string;
  serviceEndpoint: string;
}

/** W3C DID Document. */
export interface DIDDocument {
  "@context": string[];
  id: string;
  controller?: string;
  verificationMethod: VerificationMethod[];
  authentication: string[];
  assertionMethod: string[];
  service?: ServiceEndpoint[];
}

// ---------------------------------------------------------------------------
// Resolution result
// ---------------------------------------------------------------------------

/** Metadata about the DID resolution itself. */
export interface DIDResolutionMetadata {
  contentType?: string;
  error?: "invalidDid" | "notFound" | "internalError";
  /** Duration of the resolution in milliseconds. */
  duration?: number;
}

/** Metadata about the DID document (on-chain anchoring info). */
export interface DIDDocumentMetadata {
  /** ISO-8601 creation timestamp. */
  created?: string;
  /** ISO-8601 last-update timestamp. */
  updated?: string;
  /** XRPL transaction hash that anchored the DID. */
  txHash?: string;
  /** Ledger index where the DID was anchored. */
  ledgerIndex?: number;
  /** SHA-256 hash of the canonical DID document stored on-chain. */
  dataHash?: string;
}

/** Full DID resolution result per the DID Resolution specification. */
export interface DIDResolutionResult {
  didResolutionMetadata: DIDResolutionMetadata;
  didDocument: DIDDocument | null;
  didDocumentMetadata: DIDDocumentMetadata;
}

// ---------------------------------------------------------------------------
// MPT (Multi-Purpose Token) identity
// ---------------------------------------------------------------------------

/** On-chain agent identity token metadata. */
export interface MPTMetadata {
  /** Human-readable agent name. */
  name: string;
  /** Agent role. */
  role: string;
  /** ISO-8601 creation timestamp. */
  created: string;
  /** Issuing organisation or network name. */
  owner: string;
  /** Schema version. */
  version: number;
}

/** Resolved MPT identity record. */
export interface MPTRecord {
  /** MPTokenIssuanceID on XRPL. */
  mptId: string;
  /** Transaction hash of the minting tx. */
  txHash: string;
  /** Decoded metadata. */
  metadata: MPTMetadata;
  /** Ledger index of the minting tx. */
  ledgerIndex: number;
  /** XRPL account that minted the token. */
  account: string;
}

// ---------------------------------------------------------------------------
// W3C Verifiable Credential
// ---------------------------------------------------------------------------

/** Compliance block inside a credential subject. */
export interface ComplianceInfo {
  framework: string[];
  status: "compliant" | "pending" | "non-compliant";
  lastAssessment?: string;
}

/** Credential subject describing an agent. */
export interface AgentCredentialSubject {
  id: string;
  type: string;
  name: string;
  role: string;
  owner: {
    type: "XRPLAccount";
    address: string;
  };
  capabilities?: string[];
  compliance?: ComplianceInfo;
}

/** W3C Verifiable Credential for an agent identity. */
export interface AgentCredential {
  "@context": string[];
  type: string[];
  issuer: {
    id: string;
    name: string;
    type: string;
  };
  validFrom: string;
  validUntil?: string;
  credentialSubject: AgentCredentialSubject;
  credentialStatus?: {
    type: string;
    revocationEndpoint?: string;
  };
}
