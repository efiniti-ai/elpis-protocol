import { ElpisVerifier, sha256Hex } from "@elpis-protocol/elpis-crypto";
import { KeyResolver } from "./key-resolver.js";
import type { ElpisAgent, ElpisGateOptions, ElpisRequestInfo, Request, Response, NextFunction } from "./types.js";

export function elpisGate(opts: ElpisGateOptions = {}) {
  const maxDriftMs = opts.maxDriftMs ?? 300_000;
  const resolver = new KeyResolver(opts);

  return function elpisGateMiddleware(req: Request, _res: Response, next: NextFunction): void {
    const did = req.headers["x-elpis-did"] as string | undefined;
    if (!did) {
      req.elpis = null;
      next();
      return;
    }

    const signature = req.headers["x-elpis-signature"] as string | undefined;
    const timestamp = req.headers["x-elpis-timestamp"] as string | undefined;
    const nonce = req.headers["x-elpis-nonce"] as string | undefined;

    const agent: ElpisAgent = {
      did,
      signature: signature ?? null,
      timestamp: timestamp ?? null,
      nonce: nonce ?? null,
      certHash: (req.headers["x-elpis-cert-hash"] as string) ?? null,
      domain: (req.headers["x-elpis-domain"] as string) ?? null,
      displayName: (req.headers["x-elpis-display-name"] as string) ?? null,
      scope: (req.headers["x-elpis-scope"] as string) ?? null,
    };

    if (!signature || !timestamp || !nonce) {
      req.elpis = { verified: false, reason: "missing_headers", agent };
      next();
      return;
    }

    const ts = new Date(timestamp).getTime();
    if (Number.isNaN(ts) || Math.abs(Date.now() - ts) > maxDriftMs) {
      req.elpis = { verified: false, reason: "timestamp_expired", agent };
      next();
      return;
    }

    resolver.resolve(did).then((publicKeyHex) => {
      if (!publicKeyHex) {
        req.elpis = { verified: false, reason: "unknown_did", agent };
        return next();
      }

      const rawBody = (req as Request & { rawBody?: Buffer }).rawBody ?? Buffer.alloc(0);
      const verifier = new ElpisVerifier(Buffer.from(publicKeyHex, "hex"));
      const result = verifier.verify({
        method: req.method,
        url: req.originalUrl,
        body: rawBody,
        headers: req.headers as Record<string, string | undefined>,
      });

      req.elpis = {
        verified: result.valid,
        reason: result.valid ? "verified" : (result.reason ?? "invalid_signature"),
        agent,
      };
      next();
    }).catch((err: Error) => {
      req.elpis = { verified: false, reason: "resolution_error", agent };
      next();
    });
  };
}
