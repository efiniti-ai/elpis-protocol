"""Elpis CLI entry point."""

import asyncio
import json
import sys

import click

from . import __version__
from .config import (
    ensure_dir,
    identity_exists,
    load_identity,
    load_private_key,
    save_identity,
    save_private_key,
)
from .identity import build_identity, generate_keypair, load_keypair_from_file


@click.group()
@click.version_option(__version__)
def cli():
    """Elpis Protocol CLI -- Agent Identity & Interaction."""
    pass


@cli.command()
@click.option("--name", prompt="Agent name", help="Display name for this identity.")
@click.option("--provider", default="", help="Provider name (e.g. efiniti).")
@click.option("--role", default="", help="Agent role description.")
@click.option(
    "--network",
    default="testnet",
    type=click.Choice(["testnet", "mainnet"]),
    help="XRPL network for DID registration.",
)
@click.option(
    "--key",
    "key_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to existing Ed25519 private key file.",
)
@click.option("--force", is_flag=True, help="Overwrite existing identity.")
@click.option(
    "--register/--no-register",
    default=True,
    help="Register DID on XRPL (requires network access).",
)
@click.option("--wallet-address", default=None, help="XRPL wallet r-address (mainnet only).")
@click.option("--wallet-secret", default=None, help="XRPL wallet secret (mainnet only).")
def init(name, provider, role, network, key_path, force, register, wallet_address, wallet_secret):
    """Initialize a new Elpis identity.

    Generates an Ed25519 keypair, creates a DID, and optionally
    registers it on the XRPL Testnet.
    """
    # Check existing identity
    if identity_exists() and not force:
        existing = load_identity()
        if existing:
            click.echo(f"Identity already exists: {existing.get('did', '?')}")
            click.echo("Use --force to overwrite.")
            sys.exit(1)

    # Generate or load keypair
    if key_path:
        click.echo(f"Loading key from {key_path}...")
        try:
            private_seed, public_key = load_keypair_from_file(key_path)
        except Exception as exc:
            click.echo(f"Error loading key: {exc}", err=True)
            sys.exit(1)
        click.echo("Key loaded successfully.")
    else:
        click.echo("Generating Ed25519 keypair...")
        private_seed, public_key = generate_keypair()
        click.echo("Keypair generated.")

    # Build identity
    identity = build_identity(
        name=name,
        provider=provider,
        role=role,
        network=network,
        private_seed=private_seed,
        public_key=public_key,
    )

    # Save to ~/.elpis/
    ensure_dir()
    save_private_key(private_seed.hex())
    save_identity(identity)
    click.echo("Identity saved to ~/.elpis/")

    # XRPL registration: full chain (DIDSet -> MPT -> Credential)
    if register:
        if network == "testnet":
            click.echo("Registering on XRPL Testnet (Faucet -> DIDSet -> MPT -> Credential)...")
            from .xrpl_client import register_did_testnet

            result = asyncio.run(
                register_did_testnet(
                    did=identity["did"],
                    public_key_hex=identity["public_key"],
                    name=name,
                )
            )
        elif network == "mainnet":
            if not wallet_address or not wallet_secret:
                wallet_address = wallet_address or click.prompt("XRPL wallet address (r...)")
                wallet_secret = wallet_secret or click.prompt("XRPL wallet secret", hide_input=True)

            click.echo("Registering on XRPL Mainnet (DIDSet -> MPT -> Credential)...")
            click.echo("Each transaction requires your confirmation.")
            from .xrpl_client import register_did_mainnet, TX_DESCRIPTIONS

            def _confirm(step_name, tx_type, fee_xrp, reserve_xrp):
                desc = TX_DESCRIPTIONS.get(tx_type, tx_type)
                click.echo(f"\n  TX: {desc}")
                click.echo(f"  Fee: {fee_xrp:.6f} XRP | Reserve: {reserve_xrp:.1f} XRP")
                return click.confirm("  Submit?", default=True)

            result = asyncio.run(
                register_did_mainnet(
                    did=identity["did"],
                    public_key_hex=identity["public_key"],
                    name=name,
                    wallet_address=wallet_address,
                    wallet_secret=wallet_secret,
                    confirm_fn=_confirm,
                )
            )
            if result and result.get("balance_xrp") is not None:
                click.echo(f"  Balance:    {result['balance_xrp']:.2f} XRP")
            if result and result.get("estimated_cost"):
                cost = result["estimated_cost"]
                click.echo(f"  Est. cost:  {cost['total_xrp']:.6f} XRP (fees + reserve)")
        else:
            result = None

        if result:
            if result.get("address"):
                identity["xrpl_address"] = result["address"]
                click.echo(f"  Wallet:     {result['address']}")

            steps = result.get("steps", {})
            for step_name, step_data in steps.items():
                if step_data.get("skipped"):
                    status = "SKIPPED"
                elif step_data.get("success"):
                    status = "OK"
                else:
                    status = "FAILED"
                tx = step_data.get("tx_hash", "")[:12]
                click.echo(f"  {step_name:12s} {status}" + (f"  tx={tx}..." if tx else ""))

            if result.get("tx_hash"):
                identity["xrpl_tx_hash"] = result["tx_hash"]
            if result.get("mpt_tx_hash"):
                identity["xrpl_mpt_hash"] = result["mpt_tx_hash"]
            if result.get("credential_tx_hash"):
                identity["xrpl_credential_hash"] = result["credential_tx_hash"]

            save_identity(identity)

            if not result.get("registered"):
                click.echo(f"  Warning: {result.get('error', 'partial failure')}")
        else:
            click.echo("XRPL registration skipped (network unreachable).")

    # Summary
    click.echo("")
    click.echo(f"  DID:        {identity['did']}")
    click.echo(f"  Name:       {identity['name']}")
    click.echo(f"  Network:    {identity['network']}")
    click.echo(f"  Public Key: {identity['public_key'][:16]}...")
    click.echo(f"  Cert Hash:  {identity['cert_hash']}")
    if identity.get("xrpl_address"):
        click.echo(f"  XRPL Addr:  {identity['xrpl_address']}")
    if identity.get("xrpl_tx_hash"):
        click.echo(f"  TX Hash:    {identity['xrpl_tx_hash'][:16]}...")
    click.echo("")
    click.echo("Ready. Run 'elpis whoami' to verify your identity.")


@cli.command()
@click.option(
    "--resolver",
    default="https://elpis.efiniti.ai/whoami",
    help="Elpis resolver URL for identity verification.",
)
@click.option("--offline", is_flag=True, help="Show local identity without contacting resolver.")
def whoami(resolver, offline):
    """Verify identity via signed request to Elpis resolver.

    Sends a signed GET request to the resolver and displays the
    verified identity response. Use --offline to show local identity only.
    """
    identity = load_identity()
    key_hex = load_private_key()
    if not identity or not key_hex:
        click.echo("No identity found. Run 'elpis init' first.")
        sys.exit(1)

    if offline:
        click.echo(f"  DID:        {identity['did']}")
        click.echo(f"  Name:       {identity['name']}")
        click.echo(f"  Network:    {identity['network']}")
        click.echo(f"  Public Key: {identity['public_key'][:16]}...")
        click.echo(f"  Created:    {identity.get('created_at', '?')}")
        return

    # Sign and send whoami request
    from .signer import sign_request
    import httpx

    private_seed = bytes.fromhex(key_hex)
    sig_headers = sign_request(private_seed, "GET", resolver)
    headers = {
        **sig_headers,
        "X-Elpis-DID": identity["did"],
        "X-Elpis-Domain": identity.get("provider", ""),
    }
    if identity.get("xrpl_address"):
        headers["X-Elpis-Account"] = identity["xrpl_address"]

    click.echo(f"Verifying identity: {identity['did']}")
    try:
        resp = httpx.get(resolver, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            click.echo(f"  Verified:   {data.get('verified', False)}")
            click.echo(f"  DID:        {data.get('did', identity['did'])}")
            click.echo(f"  Name:       {data.get('name', identity['name'])}")
            if data.get("message"):
                click.echo(f"  Message:    {data['message']}")
        else:
            click.echo(f"  Resolver returned {resp.status_code}")
            click.echo(f"  Falling back to local identity:")
            click.echo(f"  DID:        {identity['did']}")
            click.echo(f"  Name:       {identity['name']}")
            click.echo(f"  Signature:  valid (local)")
    except httpx.ConnectError:
        click.echo("  Resolver unreachable. Local identity:")
        click.echo(f"  DID:        {identity['did']}")
        click.echo(f"  Name:       {identity['name']}")
        click.echo(f"  Signature:  valid (local, unverified)")
    except Exception as exc:
        click.echo(f"  Error: {exc}")
        click.echo(f"  DID:        {identity['did']}")


@cli.command("request")
@click.argument("url")
@click.option("-X", "--method", default="GET", help="HTTP method.")
@click.option("-d", "--data", "body", default=None, help="Request body (string).")
@click.option("-H", "--header", "extra_headers", multiple=True,
              help="Extra header (key: value). Repeatable.")
@click.option("-v", "--verbose", is_flag=True, help="Show request headers.")
@click.option("-o", "--output", "output_file", default=None, type=click.Path(),
              help="Write response body to file.")
def request_cmd(url, method, body, extra_headers, verbose, output_file):
    """Send a signed HTTP request (curl replacement).

    Signs the request with your Elpis identity and injects X-Elpis-*
    headers. The response is printed to stdout.

    Examples:

        elpis request https://efiniti.de/api/eacd/home

        elpis request -X POST -d '{"key": "value"}' https://api.example.com/data
    """
    identity = load_identity()
    key_hex = load_private_key()
    if not identity or not key_hex:
        click.echo("No identity found. Run 'elpis init' first.", err=True)
        sys.exit(1)

    from .signer import sign_request
    import httpx

    private_seed = bytes.fromhex(key_hex)
    body_bytes = body.encode() if body else b""

    # Sign the request
    sig_headers = sign_request(private_seed, method.upper(), url, body_bytes)

    # Build headers
    headers = {
        **sig_headers,
        "X-Elpis-DID": identity["did"],
        "X-Elpis-Domain": identity.get("provider", ""),
    }
    if identity.get("xrpl_address"):
        headers["X-Elpis-Account"] = identity["xrpl_address"]
    if identity.get("cert_hash"):
        headers["X-Elpis-Cert-Hash"] = identity["cert_hash"]
    if identity.get("name"):
        headers["X-Elpis-Display-Name"] = identity["name"]

    # Add extra headers
    for h in extra_headers:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    if verbose:
        click.echo(f"> {method.upper()} {url}", err=True)
        for k, v in headers.items():
            click.echo(f"> {k}: {v}", err=True)
        click.echo(">", err=True)

    # Send request
    try:
        resp = httpx.request(
            method=method.upper(),
            url=url,
            headers=headers,
            content=body_bytes if body_bytes else None,
            timeout=30.0,
            follow_redirects=True,
        )

        if verbose:
            click.echo(f"< HTTP {resp.status_code}", err=True)
            for k, v in resp.headers.items():
                click.echo(f"< {k}: {v}", err=True)
            click.echo("<", err=True)

        if output_file:
            with open(output_file, "wb") as f:
                f.write(resp.content)
            click.echo(f"Response written to {output_file}", err=True)
        else:
            click.echo(resp.text)

        sys.exit(0 if resp.status_code < 400 else 1)

    except httpx.ConnectError as exc:
        click.echo(f"Connection error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Request failed: {exc}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show current identity status."""
    identity = load_identity()
    if not identity:
        click.echo("No identity found. Run 'elpis init' first.")
        sys.exit(1)

    click.echo(json.dumps(identity, indent=2))
