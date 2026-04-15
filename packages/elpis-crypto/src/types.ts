export interface ElpisSignatureHeaders {
  "X-Elpis-Signature": string;
  "X-Elpis-Timestamp": string;
  "X-Elpis-Nonce": string;
}

export interface ElpisHeaders extends ElpisSignatureHeaders {
  "X-Elpis-DID": string;
  "X-Elpis-Cert-Hash"?: string;
  "X-Elpis-Domain"?: string;
}

export interface VerificationResult {
  valid: boolean;
  reason?: string;
  did?: string;
  timestamp?: string;
}

export interface VerifyOptions {
  maxAge?: number;
  nonceSet?: Set<string>;
}
