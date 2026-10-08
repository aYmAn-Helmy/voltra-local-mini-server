# Voltra HTTPS via MikroTik RouterOS 7.24.5

This deployment keeps the MTTL-W01 device protocol local while publishing only the Voltra HTTP application through HTTPS.

## Current deployment

- Voltra server: `192.168.1.45:8086`
- MikroTik upstream/LAN address: `192.168.1.7`
- Upstream gateway: `192.168.1.1`
- Public hostname: `b8710ce04869.sn.mynetname.net`
- RouterOS: `7.24.5`
- ACME certificate: `voltra-cloud-le`
- MikroTik HTTPS reverse proxy: TCP 443 -> `http://192.168.1.45:8086`
- Upstream public forward: TCP 8443 -> `192.168.1.7:443`
- Verified public URL: `https://b8710ce04869.sn.mynetname.net:8443`

Do **not** expose TCP 8086, TCP 10086, or UDP 10087 directly to the Internet.

## Voltra secure environment

Generate a strong token on the Voltra host:

```bash
python scripts/generate_api_token.py
```

Store it in the deployment environment, not in Git:

```dotenv
VOLTRA_API_TOKEN=PASTE_GENERATED_TOKEN_HERE
VOLTRA_TRUSTED_PROXY=192.168.1.7/32
VOLTRA_PUBLIC_ORIGIN=https://b8710ce04869.sn.mynetname.net:8443
VOLTRA_CORS_ORIGIN=https://b8710ce04869.sn.mynetname.net:8443
```

When `VOLTRA_API_TOKEN` is set, `/health` stays public for monitoring while `/api/*` and `/voltra/api/*` require:

```http
Authorization: Bearer <token>
```

The server accepts `X-Forwarded-For` and `X-Forwarded-Proto` only when the direct peer is in `VOLTRA_TRUSTED_PROXY`.

## MikroTik certificate

The current router already has a Let's Encrypt certificate named `voltra-cloud-le`. For a rebuild, verify IP Cloud first:

```routeros
/ip cloud print
```

Then create an ACME certificate for the IP Cloud hostname using the RouterOS 7.24.5 ACME command available on the router. Verify with:

```routeros
/certificate print detail where name="voltra-cloud-le"
```

Expected DNS name:

```text
b8710ce04869.sn.mynetname.net
```

## Reverse proxy

The current target is:

```text
HTTPS :443 -> 192.168.1.45:8086
```

Verify the rule:

```routeros
/ip reverse-proxy print detail
```

If rebuilding it, configure the RouterOS reverse proxy with:

- destination IP: `192.168.1.45`
- destination port: `8086`
- SNI/public host: `b8710ce04869.sn.mynetname.net`
- certificate: `voltra-cloud-le`

Keep `www-ssl` disabled or move it away from port 443:

```routeros
/ip service print
```

## Firewall

Allow TCP 443 to the MikroTik reverse proxy from WAN. Do not add WAN accepts or destination NAT rules for 8086, 10086, or 10087.

Verify:

```routeros
/ip firewall filter print detail
```

## Upstream router

The upstream router at `192.168.1.1` has been verified with this Internet-facing forward:

```text
TCP 8443 -> 192.168.1.7:443
```

External port `443` conflicts with the upstream router's own HTTPS management service, so the current production public endpoint intentionally uses `:8443`.

The observed public address is `156.216.159.2`, matching MikroTik IP Cloud. The observed topology is normal upstream NAT rather than CGNAT.

## Tests

From the MikroTik/LAN side:

```text
https://b8710ce04869.sn.mynetname.net:8443/health
```

The expected response is HTTP 200.

With the upstream 8443 forward enabled, turn Wi-Fi off on a phone and test over mobile data:

```bash
curl -fsS https://b8710ce04869.sn.mynetname.net:8443/health
curl -fsS \
  -H "Authorization: Bearer $VOLTRA_API_TOKEN" \
  https://b8710ce04869.sn.mynetname.net:8443/voltra/api/overview
```

A request to `/voltra/api/overview` without a token should return HTTP 401 when secure mode is enabled.

This deployment was externally verified from independent Internet locations: `/health` returned HTTP 200 through `:8443`, and local TLS validation against the public hostname succeeded.

## Rollback

1. Remove/disable the upstream TCP 8443 -> `192.168.1.7:443` forward on `192.168.1.1`.
2. Disable the MikroTik reverse-proxy rule for Voltra.
3. Remove the WAN TCP 443 allow rule if it is no longer needed.
4. Keep TCP 10086 and UDP 10087 LAN-only.
5. Voltra remains accessible locally at `http://192.168.1.45:8086`.
