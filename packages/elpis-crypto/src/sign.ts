import { createHash, createPrivateKey, createPublicKey, randomUUID, sign } from "node:crypto";
import type { ElpisSignatureHeaders } from "./types.js";

const ED25519_PKCS8_PREFIX = Buffer.from("302e020100300506032b657004220420", "hex");

export function buildCanonical(method: string, url: string, bodyHash: string, timestamp: string, nonce: string): string {
  return `${method}\n${url}\n${bodyHash}\n${timestamp}\n${nonce}`;
}

export function sha256Hex(data: Uint8Array | string): string {
  return createHash("sha256").update(typeof data === "string" ? Buffer.from(data) : data).digest("hex");
}

export class ElpisSigner {
  private readonly privateKeyObject: ReturnType<typeof createPrivateKey>;
  readonly publicKey: Buffer;

  constructor(seed: Uint8Array) {
    if (seed.length !== 32) throw new Error(`Expected 32-byte Ed25519 seed, got ${seed.length} bytes`);
    this.privateKeyObject = createPrivateKey({
      key: Buffer.concat([ED25519_PKCS8_PREFIX, Buffer.from(seed)]),
      format: "der",
      type: "pkcs8",
    });
    const pubKeyObject = createPublicKey(this.privateKeyObject);
    const spki = pubKeyObject.export({ type: "spki", format: "der" }) as Buffer;
    this.publicKey = Buffer.from(spki.subarray(spki.length - 32));
  }

  sign(method: string, url: string, body: Uint8Array | string = ""): ElpisSignatureHeaders {
    const timestamp = new Date().toISOString();
    const nonce = randomUUID();
    const bodyHash = sha256Hex(body);
    const canonical = buildCanonical(method, url, bodyHash, timestamp, nonce);
    const signature = sign(null, Buffer.from(canonical), this.privateKeyObject);
    return {
      "X-Elpis-Signature": signature.toString("base64"),
      "X-Elpis-Timestamp": timestamp,
      "X-Elpis-Nonce": nonce,
    };
  }
}
