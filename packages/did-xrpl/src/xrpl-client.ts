import { Client, type AccountInfoRequest } from "xrpl";
import type { XRPLNetwork } from "./types.js";

const NETWORK_URLS: Record<XRPLNetwork, string> = {
  mainnet: "wss://xrplcluster.com",
  testnet: "wss://s.altnet.rippletest.net:51233",
  devnet: "wss://s.devnet.rippletest.net:51233",
};

export interface XRPLClientOptions {
  network?: XRPLNetwork;
  url?: string;
  poolSize?: number;
}

export class XRPLClient {
  private readonly url: string;
  readonly network: XRPLNetwork;
  private pool: Client[] = [];
  private roundRobin = 0;

  constructor(opts: XRPLClientOptions = {}) {
    this.network = opts.network ?? "testnet";
    this.url = opts.url ?? NETWORK_URLS[this.network];
    const size = Math.max(1, opts.poolSize ?? 2);
    for (let i = 0; i < size; i++) {
      this.pool.push(new Client(this.url));
    }
  }

  async connect(): Promise<void> {
    await Promise.all(this.pool.map((c) => { if (!c.isConnected()) return c.connect(); }));
  }

  async disconnect(): Promise<void> {
    await Promise.all(this.pool.map((c) => { if (c.isConnected()) return c.disconnect(); }));
  }

  private client(): Client {
    const c = this.pool[this.roundRobin % this.pool.length];
    this.roundRobin++;
    return c;
  }

  async getAccountInfo(address: string): Promise<Record<string, unknown> | null> {
    try {
      const req: AccountInfoRequest = { command: "account_info", account: address, ledger_index: "validated" };
      const resp = await this.client().request(req);
      return resp.result.account_data as unknown as Record<string, unknown>;
    } catch (err: unknown) {
      if (isActNotFound(err)) return null;
      throw err;
    }
  }

  async getAccountObjects(address: string, type?: string): Promise<Record<string, unknown>[]> {
    const objects: Record<string, unknown>[] = [];
    let marker: unknown;
    do {
      const resp: { result: { account_objects: Record<string, unknown>[]; marker?: unknown } } = await this.client().request({
        command: "account_objects", account: address, type, ledger_index: "validated", marker, limit: 200,
      } as never);
      const result = resp.result;
      objects.push(...result.account_objects);
      marker = result.marker;
    } while (marker);
    return objects;
  }

  async getDIDObject(address: string): Promise<Record<string, unknown> | null> {
    const objects = await this.getAccountObjects(address, "did");
    return objects.find((o) => o.LedgerEntryType === "DID") ?? null;
  }

  async getMPTokenIssuances(address: string): Promise<Record<string, unknown>[]> {
    const objects = await this.getAccountObjects(address);
    return objects.filter((o) => o.LedgerEntryType === "MPTokenIssuance");
  }
}

function isActNotFound(err: unknown): boolean {
  if (err && typeof err === "object" && "data" in err) {
    const data = (err as { data?: { error?: string } }).data;
    return data?.error === "actNotFound";
  }
  return false;
}
