#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { ElpisSigner } from "@elpis-protocol/elpis-crypto";

interface CliArgs {
  keyHex: string;
  did?: string;
  domain?: string;
  method: string;
  url: string;
  body: string;
  verbose: boolean;
}

function usage(): never {
  console.error(`elpis-curl -- Elpis Protocol signed HTTP client\n\nUsage:\n  elpis-curl [options] METHOD URL [BODY]\n\nOptions:\n  --key <file>      Path to hex-encoded Ed25519 seed file\n  --did <did>       DID to include in X-Elpis-DID header\n  --domain <domain> Domain for X-Elpis-Domain header\n  -v, --verbose     Print request/response details to stderr\n\nEnvironment:\n  ELPIS_KEY         Hex-encoded Ed25519 seed (alternative to --key)\n  ELPIS_DID         Default DID (alternative to --did)\n  ELPIS_DOMAIN      Default domain (alternative to --domain)\n\nBody:\n  Pass "-" to read from stdin.`);
  process.exit(1);
}

function parseArgs(argv: string[]): CliArgs {
  let keyHex = process.env.ELPIS_KEY ?? "";
  let did = process.env.ELPIS_DID;
  let domain = process.env.ELPIS_DOMAIN;
  let verbose = false;
  const positional: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--key" && i + 1 < argv.length) { keyHex = readFileSync(argv[++i], "utf-8").trim(); }
    else if (arg === "--did" && i + 1 < argv.length) { did = argv[++i]; }
    else if (arg === "--domain" && i + 1 < argv.length) { domain = argv[++i]; }
    else if (arg === "-v" || arg === "--verbose") { verbose = true; }
    else if (arg === "--help" || arg === "-h") { usage(); }
    else { positional.push(arg); }
  }
  if (positional.length < 2) usage();
  if (!keyHex) { console.error("Error: No signing key. Use --key <file> or ELPIS_KEY env."); process.exit(1); }
  let body = positional[2] ?? "";
  if (body === "-") body = readFileSync(0, "utf-8");
  return { keyHex, did, domain, method: positional[0].toUpperCase(), url: positional[1], body, verbose };
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const seed = Buffer.from(args.keyHex, "hex");
  const signer = new ElpisSigner(seed);
  const sigHeaders = signer.sign(args.method, args.url, args.body);
  const headers: Record<string, string> = { ...sigHeaders };
  if (args.did) headers["X-Elpis-DID"] = args.did;
  if (args.domain) headers["X-Elpis-Domain"] = args.domain;
  if (args.body) headers["Content-Type"] = "application/json";
  if (args.verbose) {
    console.error(`> ${args.method} ${args.url}`);
    for (const [k, v] of Object.entries(headers)) console.error(`> ${k}: ${v}`);
    if (args.body) console.error(`> Body: ${args.body.substring(0, 200)}...`);
    console.error("");
  }
  const resp = await fetch(args.url, {
    method: args.method,
    headers,
    body: args.method !== "GET" && args.method !== "HEAD" ? args.body || undefined : undefined,
  });
  if (args.verbose) {
    console.error(`< ${resp.status} ${resp.statusText}`);
    for (const [k, v] of resp.headers.entries()) console.error(`< ${k}: ${v}`);
    console.error("");
  }
  const respBody = await resp.text();
  process.stdout.write(respBody);
  if (!resp.ok) process.exit(1);
}

main().catch((err) => { console.error(`Error: ${err.message}`); process.exit(1); });
