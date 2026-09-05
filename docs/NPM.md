# Nginx Proxy Manager — automated reference routing

`stream-stack` treats Nginx Proxy Manager as desired state. It does not copy a private NPM database or private certificate material from another installation.

The normal setup path is:

```bash
./setup.sh
```

The current adapter is `scripts/npm_current.py`, which extends the generic `npm_apply.py` logic with the exact current topology, LAN-only restrictions and public-DNS wait used by the one-click wizard.

## Router prerequisite

For a fresh public install, forward **before** running the wizard:

```text
TCP 80  -> SERVER_LAN_IP:80
TCP 443 -> SERVER_LAN_IP:443
```

TCP 80 is required for Let's Encrypt HTTP-01. TCP 443 is used by the final HTTPS path.

## Public DNS wait

After Cloudflare DDNS starts, `npm_current.py` queries Cloudflare DNS-over-HTTPS and waits until every selected hostname has become publicly resolvable.

Timeout:

```text
PUBLIC_READY_TIMEOUT=600
```

The certificate request starts only after this wait succeeds. This avoids the common race between record creation and immediate HTTP-01 validation.

## Hostnames

`BASE_DOMAIN` supplies defaults, but every managed hostname may be overridden in `setup.env`.

Example:

```text
AIOSTREAMS_HOST=aio.example.org
MEDIAFLOW_HOST=proxy.example.net
EASYPROXY_HOST=easy.example.net
HEADSCALE_HOST=mesh.example.org
```

The same values are propagated to service configs, OAuth, DDNS, certificates and NPM.

## Current proxy topology

| Setting | Target | Port | WebSocket | Access |
|---|---|---:|---:|---|
| `AIOSTREAMS_HOST` | `aiostreams` | 4444 | no | public |
| `AIOMETADATA_HOST` | `aiometadata` | 1337 | yes | public |
| `MEDIAFLOW_HOST` | `mediaflow-proxy-light` | 8888 | no | public |
| `EASYPROXY_HOST` | `easyproxy` | 8760 | no | public |
| `HEADSCALE_HOST` | `headscale` | 8080 | yes | public |
| `PORTAINER_HOST` | `portainer` | 9000 | no | LAN-only |
| `STREMTHRU_HOST` | `gluetun` | 9090 | no | LAN-only |
| `SEANIME_HOST` | `gluetun` | 43211 | yes | public |
| `SEANIME_SHARED_HOST` | `gluetun` | 43311 | yes | public |
| `COMETNET_HOST` | `gluetun` | 8765 | yes | public |
| `STREAMVIX_HOST` | `streamvix` | 7860 | no | LAN-only |
| `TVVOO_HOST` | `tvvoo` | 5000 | no | LAN-only |
| `AIOMANAGER_HOST` | `aiomanager` | 1610 | yes | LAN-only |

For LAN-only hosts, the generated Nginx advanced block uses the configured `LAN_SUBNET`:

```nginx
allow <LAN_SUBNET>;
deny all;
```

EasyProxy remains public because playback clients may consume it directly.

Comet itself remains local/internal on port `2020`.

## Common NPM settings

Every managed host receives:

- shared SSL certificate;
- Force SSL;
- HTTP/2;
- HSTS;
- HSTS subdomains;
- Block Common Exploits;
- caching disabled;
- WebSocket enabled only where required.

## NPM administrator

Relevant settings:

```text
NPM_ADMIN_EMAIL=
NPM_ADMIN_PASSWORD=
LETSENCRYPT_EMAIL=
AUTO_CONFIGURE_NPM=true
```

Defaults:

- blank `NPM_ADMIN_EMAIL` -> `ALLOWED_EMAIL`;
- blank `NPM_ADMIN_PASSWORD` -> generated locally;
- blank `LETSENCRYPT_EMAIL` -> `ALLOWED_EMAIL`.

On a fresh NPM DB, the supported `INITIAL_ADMIN_*` variables are injected. On an existing DB they do not overwrite the current account, so put the existing NPM credentials in `setup.env` when rerunning against an established installation.

## Shared certificate

The setup requests one Let's Encrypt certificate containing the exact selected SAN hostnames.

Cloudflare DDNS is started first and the current reference mode is DNS-only (`PROXIED=false`) so HTTP-01 can reach NPM directly.

If certificate issuance fails after public DNS is ready, the error explicitly points back to:

```text
TCP 80
TCP 443
SERVER_LAN_IP
Cloudflare DNS/token permissions
```

## Headscale + Headplane + OAuth2 Proxy

`HEADSCALE_HOST` serves:

```text
/                 -> Headscale
/admin            -> OAuth2 Proxy -> Headplane
/oauth2/*          -> OAuth2 Proxy
/oauth2/callback   -> OAuth2 Proxy
```

The advanced Nginx block is generated dynamically from the selected hostname. Headplane's own OIDC layer remains disabled; OAuth2 Proxy is the authentication layer.

## Idempotency

Each run:

1. resolves the desired hostnames;
2. updates DDNS;
3. waits for public DNS;
4. authenticates to NPM;
5. reuses a certificate when possible or creates one;
6. updates matching proxy hosts in place or creates missing hosts;
7. leaves unrelated/manual hosts untouched;
8. verifies that every required managed hostname exists.

The non-secret desired state is also written to:

```text
data/npm/stream-stack-hosts.json
```

This file is gitignored.

## Disable automation

```bash
./setup.sh --no-npm
```

or:

```text
AUTO_CONFIGURE_NPM=false
```

## Final verification

The Windows wizard performs the strict final check automatically when `STRICT_ACCEPTANCE=true`.

CLI equivalent:

```bash
docker compose --profile all up -d
python3 scripts/acceptance.py --timeout 600
```

The acceptance test validates public non-LAN-only hostname resolution, TLS hostname/certificate checks, NPM non-5xx routing and the Headscale `/admin` OAuth path in addition to container and LAN-port readiness.
