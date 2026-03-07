import { XRPLDIDResolver } from "@elpis-protocol/did-xrpl";
import type { ElpisGateOptions } from "./types.js";

interface CachedKey {
  publicKeyHex: string;
  resolvedAt: number;
}

const BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
const BASE58_MAP = new Uint8Array(128).fill(255);
for (let i = 0; i < BASE58_ALPHABET.length; i++) BASE58_MAP[BASE58_ALPHABET.charCodeAt(i)] = i;

function base58btcDecode(str: string): Uint8Array {
  let zeros = 0;
  for (const c of str) {
    if (c === "1") zeros++;
    else break;
  }
  let num = 0n;
  for (const c of str) {
    const val = BASE58_MAP[c.charCodeAt(0)];
    if (val === 255) throw new Error("Invalid base58 character");
    num = num * 58n + BigInt(val);
  }
  const hex = num.toString(16);
  const padded = hex.length % 2 ? "0" + hex : hex;
  const bytes = Buffer.from(padded, "hex");
  const result = new Uint8Array(zeros + bytes.length);
  result.set(bytes, zeros);
  return result;
}

function decodeMultibaseKey(multibase: string): string | null {
  if (!multibase || !multibase.startsWith("z")) return null;
  try {
    const bytes = base58btcDecode(multibase.slice(1));
    if (bytes.length === 34 && bytes[0] === 0xed && bytes[1] === 0x01) {
      return Buffer.from(bytes.subarray(2)).toString("hex");
    }
    if (bytes.length === 32) return Buffer.from(bytes).toString("hex");
    return null;
  } catch {
    return null;
  }
}

export class KeyResolver {
  private cache = new Map<string, CachedKey>();
  private cacheTtl: number;
  private didResolverUrl?: string;
  private xrplResolver?: XRPLDIDResolver;
  private trustStore: Record<string, string>;

  constructor(opts: ElpisGateOptions = {}) {
    this.cacheTtl = opts.keyCacheTtlMs ?? 3_600_000;
    this.didResolverUrl = opts.didResolverUrl;
    this.trustStore = opts.trustStore ?? {};

    if (opts.useOnChainResolution) {
      this.xrplResolver = new XRPLDIDResolver({ network: opts.xrplNetwork ?? "testnet" });
    }
  }

  async resolve(did: string): Promise<string | null> {
    const cached = this.cache.get(did);
    if (cached && (Date.now() - cached.resolvedAt) < this.cacheTtl) {
      return cached.publicKeyHex;
    }

    // 1. HTTP DID Resolution
    if (this.didResolverUrl) {
      const key = await this.resolveHTTP(did);
      if (key) return this.cacheAndReturn(did, key);
    }

    // 2. On-chain XRPL DID Resolution
    if (this.xrplResolver) {
      const key = await this.resolveOnChain(did);
      if (key) return this.cacheAndReturn(did, key);
    }

    // 3. Static trust store fallback
    const trusted = this.trustStore[did];
    if (trusted) return this.cacheAndReturn(did, trusted);

    return null;
  }

  private async resolveHTTP(did: string): Promise<string | null> {
    try {
      const url = this.didResolverUrl!.includes("{did}")
        ? this.didResolverUrl!.replace("{did}", encodeURIComponent(did))
        : this.didResolverUrl + "/" + encodeURIComponent(did);
      const resp = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (!resp.ok) return null;
      const result = await resp.json() as Record<string, unknown>;
      return this.extractKeyFromDIDDocument(result);
    } catch {
      return null;
    }
  }

  private async resolveOnChain(did: string): Promise<string | null> {
    try {
      await this.xrplResolver!.connect();
      const result = await this.xrplResolver!.resolve(did);
      if (!result.didDocument?.verificationMethod?.length) return null;
      const vm = result.didDocument.verificationMethod[0];
      return vm.publicKeyMultibase ? decodeMultibaseKey(vm.publicKeyMultibase) : null;
    } catch {
      return null;
    }
  }

  private extractKeyFromDIDDocument(result: Record<string, unknown>): string | null {
    const doc = (result as { didDocument?: Record<string, unknown> }).didDocument ?? result;
    const methods = (doc as { verificationMethod?: Array<Record<string, string>> }).verificationMethod;
    const vm = methods?.[0];
    if (!vm) return null;
    if (vm.publicKeyMultibase) return decodeMultibaseKey(vm.publicKeyMultibase);
    if (vm.publicKeyHex) return vm.publicKeyHex;
    return null;
  }

  private cacheAndReturn(did: string, publicKeyHex: string): string {
    this.cache.set(did, { publicKeyHex, resolvedAt: Date.now() });
    return publicKeyHex;
  }

  async disconnect(): Promise<void> {
    if (this.xrplResolver) await this.xrplResolver.disconnect();
  }
}
