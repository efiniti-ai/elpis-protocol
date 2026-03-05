### 3.1.1 Normative Canonicalization Specification

The canonical string construction described in Section 3.1 requires precise normalization rules to ensure that independently implemented signers and verifiers produce identical canonical strings for the same logical request. This section provides the normative specification in ABNF (RFC 5234).

#### ABNF Grammar

```abnf
canonical-string = method LF url LF body-hash LF timestamp LF nonce

method           = 1*UPALPHA
                 ; HTTP method in uppercase: "GET", "POST", "PUT",
                 ; "DELETE", "PATCH", "HEAD", "OPTIONS"

url              = scheme "://" authority path-abempty ["?" query]
                 ; Fully normalized URL per rules below

body-hash        = 64HEXDIG
                 ; Lowercase hex-encoded SHA-256 of request body
                 ; For bodyless requests: SHA-256 of empty string
                 ; = "e3b0c44298fc1c149afbf4c8996fb924
                 ;    27ae41e4649b934ca495991b7852b855"

timestamp        = date-fullyear "-" date-month "-" date-mday
                   "T" time-hour ":" time-minute ":" time-second "Z"
                 ; ISO 8601 UTC only, no timezone offset variants

nonce            = 8HEXDIG "-" 4HEXDIG "-" "4" 3HEXDIG "-"
                   variant 3HEXDIG "-" 12HEXDIG
                 ; UUID v4 in lowercase canonical form (RFC 9562)

variant          = %x38-39 / %x61-62
                 ; '8', '9', 'a', or 'b'

LF               = %x0A  ; Line Feed (not CRLF)

UPALPHA          = %x41-5A  ; A-Z

HEXDIG           = DIGIT / %x61-66  ; 0-9, a-f (lowercase only)
```

#### URL Normalization Rules

The URL component MUST be normalized before inclusion in the canonical string. The following rules are applied in order:

1. **Scheme**: Lowercase. `HTTPS` → `https`.
2. **Host**: Lowercase. `API.Example.COM` → `api.example.com`.
3. **Port**: Omit default ports. `https://api.example.com:443/` → `https://api.example.com/`. Non-default ports are preserved: `https://api.example.com:8443/`.
4. **Path**: Resolve `.` and `..` segments (RFC 3986 Section 5.2.4). Preserve trailing slash. Percent-encode reserved characters per RFC 3986. Decode unreserved characters: `%41` → `A`. Normalize percent-encoding to uppercase: `%2f` → `%2F`.
5. **Query Parameters**: Sort lexicographically by key, then by value for duplicate keys. Preserve empty values: `key=` is distinct from `key`. Percent-encode consistently per rule 4.
6. **Fragment**: Remove entirely. Fragment identifiers (`#section`) are never sent to the server and MUST NOT be included.

#### Normalization Examples

```
Input:  HTTPS://API.Example.COM:443/v1/Data/../users?page=2&count=10&page=1
Output: https://api.example.com/v1/users?count=10&page=1&page=2

Input:  https://api.example.com/search?q=hello+world&lang=en#results
Output: https://api.example.com/search?lang=en&q=hello+world

Input:  https://api.example.com:8443/v1/data?
Output: https://api.example.com:8443/v1/data
```

#### Body Hash Rules

1. The body hash MUST be computed over the raw request body bytes, not a decoded or parsed representation.
2. For requests with no body (GET, HEAD, DELETE without body, OPTIONS), the hash MUST be the SHA-256 of the zero-length byte string: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
3. For requests with `Content-Encoding` (e.g., gzip), the hash is computed over the compressed body as transmitted.
4. The hash MUST be hex-encoded in lowercase.

#### Timestamp Rules

1. Timestamps MUST be in UTC, indicated by the `Z` suffix.
2. Offset variants (`+00:00`, `-05:00`) MUST NOT be used.
3. Fractional seconds MUST NOT be included. Truncate to whole seconds.
4. Verifiers MUST accept timestamps within a ±30 second window of their own clock.
5. Implementations SHOULD use NTP-synchronized clocks with drift ≤1 second.

#### Nonce Rules

1. Nonces MUST be UUID v4 (RFC 9562) in lowercase canonical form.
2. Verifiers MUST reject previously-seen nonces within the timestamp validity window.
3. Nonce storage MAY be pruned for entries older than 60 seconds (2× the timestamp window).

#### Canonical String Assembly

The five components are joined by a single Line Feed character (`0x0A`). No trailing Line Feed is appended. The resulting string is encoded as UTF-8 before signing.

**Complete Example:**

```
POST\nhttps://api.example.com/v1/data?page=1\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n2026-03-02T12:00:00Z\n550e8400-e29b-41d4-a716-446655440000
```

Rendered with visible line breaks:
```
POST
https://api.example.com/v1/data?page=1
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
2026-03-02T12:00:00Z
550e8400-e29b-41d4-a716-446655440000
```

#### Relationship to IETF HTTP Message Signatures (RFC 9421)

RFC 9421 defines a general mechanism for HTTP message signing with component identifiers and signature parameters. Elpis deliberately uses a simplified canonical string rather than adopting RFC 9421 directly, for the following reasons:

1. **Simplicity**: Elpis signs 5 fixed fields. RFC 9421 requires negotiating which components to sign, managing `@signature-params`, and handling derived components — complexity that serves no purpose when the signer and the identity mechanism are co-located in the proxy.
2. **Proxy Transparency**: RFC 9421 requires the signer to select headers for inclusion. Since Elpis signs at the proxy layer before headers reach the destination, some headers may not yet exist (e.g., `Content-Length` after chunked encoding). A self-contained canonical string avoids this ordering dependency.
3. **Determinism**: RFC 9421's flexibility introduces ambiguity — different implementations may select different components. Elpis' fixed canonical format guarantees identical inputs across all implementations.

Future protocol versions MAY adopt RFC 9421 component identifiers if interoperability with HTTP Message Signatures ecosystems becomes desirable. The current design prioritizes implementation simplicity and verification determinism.
