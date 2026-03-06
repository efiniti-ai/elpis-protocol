export { XRPLDIDResolver, parseDID, publicKeyToMultibase, hashDIDDocument } from "./resolver.js";
export { XRPLClient } from "./xrpl-client.js";
export type {
  XRPLDID, XRPLNetwork, DIDDocument, DIDDocumentMetadata, DIDResolutionMetadata,
  DIDResolutionResult, VerificationMethod, ServiceEndpoint, MPTMetadata, MPTRecord,
  AgentCredential, AgentCredentialSubject, ComplianceInfo,
} from "./types.js";
export type { XRPLClientOptions } from "./xrpl-client.js";
export type { XRPLDIDResolverOptions } from "./resolver.js";
