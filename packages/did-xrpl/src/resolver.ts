import { createHash } from "node:crypto";
import { XRPLClient, type XRPLClientOptions } from "./xrpl-client.js";
import type {
  DIDDocument, DIDDocumentMetadata, DIDResolutionMetadata,
  DIDResolutionResult, VerificationMethod, XRPLDID, XRPLNetwork,
} from "./types.js";

const BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

function base58btcEncode(bytes: Uint8Array): string {
  let zeros = 0;
  for (const b of bytes) { if (b === 0) break; zeros++; }
  let num = BigInt("0x" + Buffer.from(bytes).toString("hex"));
  const chars: string[] = [];
  while (num > 0n) {
    const rem = Number(num % 58n);
    chars.push(BASE58_ALPHABET[rem]);
    num = num / 58n;
  }
  return "1".repeat(zeros) + chars.reverse().join("");
}

export function publicKeyToMultibase(publicKeyBytes: Uint8Array): string {
  const prefixed = new Uint8Array(2 + publicKeyBytes.length);
  prefixed[0] = 0xed;
  prefixed[1] = 0x01;
  prefixed.set(publicKeyBytes, 2);
  return "z" + base58btcEncode(prefixed);
}

const DID_REGEX = /^did:xrpl:(\w+):(r[a-zA-Z0-9]{24,34})(?:#(.+))?$/;

export function parseDID(did: string): XRPLDID {
  const m = did.match(DID_REGEX);
  if (!m) throw new Error(`Invalid did:xrpl format: ${did}`);
  return { did, network: m[1] as XRPLNetwork, address: m[2], fragment: m[3] };
}

export interface XRPLDIDResolverOptions extends XRPLClientOptions {
  httpEndpoint?: string;
}

export class XRPLDIDResolver {
  private client: XRPLClient;
  private httpEndpoint?: string;

  constructor(opts: XRPLDIDResolverOptions = {}) {
    this.client = new XRPLClient(opts);
    this.httpEndpoint = opts.httpEndpoint;
  }

  async connect(): Promise<void> { await this.client.connect(); }
  async disconnect(): Promise<void> { await this.client.disconnect(); }

  async resolve(did: string): Promise<DIDResolutionResult> {
    const t0 = Date.now();
    let parsed: XRPLDID;
    try { parsed = parseDID(did); } catch {
      return { didResolutionMetadata: { error: "invalidDid", duration: Date.now() - t0 }, didDocument: null, didDocumentMetadata: {} };
    }
    try {
      if (this.httpEndpoint) return await this.resolveHTTP(parsed, t0);
      return await this.resolveOnChain(parsed, t0);
    } catch {
      return { didResolutionMetadata: { error: "internalError", duration: Date.now() - t0 }, didDocument: null, didDocumentMetadata: {} };
    }
  }

  private async resolveOnChain(parsed: XRPLDID, t0: number): Promise<DIDResolutionResult> {
    const accountInfo = await this.client.getAccountInfo(parsed.address);
    if (!accountInfo) {
      return { didResolutionMetadata: { error: "notFound", duration: Date.now() - t0 }, didDocument: null, didDocumentMetadata: {} };
    }
    const didObject = await this.client.getDIDObject(parsed.address);
    const docMetadata: DIDDocumentMetadata = {};
    if (didObject) {
      if (typeof didObject.Data === "string") docMetadata.dataHash = didObject.Data as string;
    }
    const publicKeyHex = accountInfo.RegularKey ? undefined : (accountInfo.PublicKey as string | undefined);
    const ownerDID = `did:xrpl:${parsed.network}:${parsed.address}`;
    const subjectDID = parsed.fragment ? `${ownerDID}#${parsed.fragment}` : ownerDID;
    const verificationMethods: VerificationMethod[] = [];
    if (publicKeyHex) {
      const keyBytes = Buffer.from(publicKeyHex, "hex");
      const ed25519Bytes = keyBytes.length === 33 && keyBytes[0] === 0xed ? keyBytes.subarray(1) : keyBytes;
      verificationMethods.push({
        id: `${subjectDID}#key-1`,
        type: "Ed25519VerificationKey2020",
        controller: ownerDID,
        publicKeyMultibase: publicKeyToMultibase(ed25519Bytes),
      });
    }
    const doc: DIDDocument = {
      "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/suites/ed25519-2020/v1"],
      id: subjectDID,
      controller: parsed.fragment ? ownerDID : undefined,
      verificationMethod: verificationMethods,
      authentication: verificationMethods.map((m) => m.id),
      assertionMethod: verificationMethods.map((m) => m.id),
    };
    return { didResolutionMetadata: { contentType: "application/did+ld+json", duration: Date.now() - t0 }, didDocument: doc, didDocumentMetadata: docMetadata };
  }

  private async resolveHTTP(parsed: XRPLDID, t0: number): Promise<DIDResolutionResult> {
    const url = this.httpEndpoint!.replace("{address}", parsed.address).replace("{fragment}", parsed.fragment ?? "").replace("{network}", parsed.network);
    const resp = await fetch(url);
    if (!resp.ok) {
      return { didResolutionMetadata: { error: resp.status === 404 ? "notFound" : "internalError", duration: Date.now() - t0 }, didDocument: null, didDocumentMetadata: {} };
    }
    const body = await resp.json();
    const didDocument: DIDDocument = body.didDocument ?? body;
    return { didResolutionMetadata: { contentType: "application/did+ld+json", duration: Date.now() - t0 }, didDocument, didDocumentMetadata: body.didDocumentMetadata ?? {} };
  }
}

export function hashDIDDocument(doc: DIDDocument): string {
  const canonical = JSON.stringify(doc, Object.keys(doc).sort());
  return createHash("sha256").update(canonical).digest("hex");
}
