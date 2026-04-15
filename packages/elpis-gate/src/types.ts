import type { Request, Response, NextFunction } from "express";

export interface ElpisAgent {
  did: string;
  signature: string | null;
  timestamp: string | null;
  nonce: string | null;
  certHash: string | null;
  domain: string | null;
  displayName: string | null;
  scope: string | null;
}

export interface ElpisRequestInfo {
  verified: boolean;
  reason: string;
  agent: ElpisAgent;
}

export interface ElpisGateOptions {
  /** Max allowed timestamp drift in ms (default: 300_000 = 5 min) */
  maxDriftMs?: number;
  /** Cache TTL for resolved public keys in ms (default: 3_600_000 = 1 hour) */
  keyCacheTtlMs?: number;
  /** HTTP endpoint for DID resolution. Use {did} placeholder. */
  didResolverUrl?: string;
  /** Use XRPL on-chain resolution (requires network connectivity) */
  useOnChainResolution?: boolean;
  /** XRPL network for on-chain resolution (default: "testnet") */
  xrplNetwork?: "mainnet" | "testnet" | "devnet";
  /** Static trust store: DID -> hex public key mapping as fallback */
  trustStore?: Record<string, string>;
}

declare global {
  namespace Express {
    interface Request {
      elpis?: ElpisRequestInfo | null;
    }
  }
}

export type { Request, Response, NextFunction };
