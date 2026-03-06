import { createPublicKey, verify } from "node:crypto";
import { buildCanonical, sha256Hex } from "./sign.js";
import type { VerificationResult, VerifyOptions } from "./types.js";

const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

export interface VerifyRequest {
  method: string;
  url: string;
  body?: Uint8Array | string;
  headers: Record<string, string | undefined>;
}

export class ElpisVerifier {
  private readonly publicKeyObject: ReturnType<typeof createPublicKey>;

  constructor(publicKey: Uint8Array) {
    if (publicKey.length !== 32) throw new Error(`Expected 32-byte Ed25519 public key, got ${publicKey.length} bytes`);
    this.publicKeyObject = createPublicKey({
      key: Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(publicKey)]),
      format: "der",
      type: "spki",
    });
  }

  verify(req: VerifyRequest, opts: VerifyOptions = {}): VerificationResult {
    const maxAge = opts.maxAge ?? 300;
    const h = req.headers;
    const signature = h["X-Elpis-Signature"] ?? h["x-elpis-signature"];
    const timestamp = h["X-Elpis-Timestamp"] ?? h["x-elpis-timestamp"];
    const nonce = h["X-Elpis-Nonce"] ?? h["x-elpis-nonce"];
    const did = h["X-Elpis-DID"] ?? h["x-elpis-did"];

    if (!signature || !timestamp || !nonce) {
      return { valid: false, reason: "Missing required Elpis headers (Signature, Timestamp, Nonce)", did, timestamp };
    }
    const requestTime = new Date(timestamp).getTime();
    if (Number.isNaN(requestTime)) return { valid: false, reason: "Invalid timestamp format", did, timestamp };
    const age = (Date.now() - requestTime) / 1000;
    if (age > maxAge) return { valid: false, reason: `Request too old (${Math.round(age)}s > ${maxAge}s)`, did, timestamp };
    if (age < -30) return { valid: false, reason: "Request timestamp is in the future", did, timestamp };
    if (opts.nonceSet) {
      if (opts.nonceSet.has(nonce)) return { valid: false, reason: "Duplicate nonce (replay)", did, timestamp };
      opts.nonceSet.add(nonce);
    }
    const bodyHash = sha256Hex(req.body ?? "");
    const canonical = buildCanonical(req.method, req.url, bodyHash, timestamp, nonce);
    let sigBuffer: Buffer;
    try { sigBuffer = Buffer.from(signature, "base64"); } catch {
      return { valid: false, reason: "Invalid signature encoding", did, timestamp };
    }
    const valid = verify(null, Buffer.from(canonical), this.publicKeyObject, sigBuffer);
    if (!valid) return { valid: false, reason: "Signature verification failed", did, timestamp };
    return { valid: true, did, timestamp };
  }
}

export function verifyElpisRequest(publicKey: Uint8Array, req: VerifyRequest, opts?: VerifyOptions): VerificationResult {
  return new ElpisVerifier(publicKey).verify(req, opts);
}
