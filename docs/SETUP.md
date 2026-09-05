# One-shot configuration wizard

The repository is designed so installation-specific values are entered once and the infrastructure is considered ready only after an optional strict post-deploy acceptance test.

## Recommended flow

For the most automated path use the Windows wizard. Before pressing Install on a fresh public deployment, forward:

```text
TCP 80  -> SERVER_LAN_IP:80
TCP 443 -> SERVER_LAN_IP:443
```

The recommended defaults are:

```text
AUTO_RUNTIME_KEYS=true
AUTO_CONFIGURE_NPM=true
PUBLIC_READY_TIMEOUT=600
STRICT_ACCEPTANCE=true
START_FULL_STACK=true    # Windows wizard option
```

With those settings, the Windows wizard does not show Completed until `scripts/acceptance.py` returns `ACCEPTANCE OK`.

## CLI path

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
./setup.sh
```

Then start the full stack and run acceptance:

```bash
docker compose --profile all up -d
python3 scripts/acceptance.py --timeout 600
```

Or prepare the input first:

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
docker compose --profile all up -d
python3 scripts/acceptance.py
```

`setup.env` is gitignored and mode `0600`.

## What `setup.sh` does

1. creates/loads `setup.env`;
2. asks only for missing required values in interactive mode;
3. generates local-only passwords/tokens/secrets where possible;
4. bootstraps tracked `*.example` templates into runtime files;
5. keeps shared credentials synchronized across services;
6. optionally starts Gluetun, Headscale and Jackett to obtain runtime keys;
7. validates generated files and Compose;
8. starts Cloudflare DDNS + Nginx Proxy Manager;
9. waits for public DNS propagation;
10. creates/reuses the NPM administrator and shared Let's Encrypt certificate;
11. creates/updates the current proxy topology.

The Windows wizard then optionally starts the full Compose stack and runs Strict Acceptance.

## DNS / SSL readiness

The current NPM adapter waits for Cloudflare's public DNS resolver to see every managed hostname before it requests the Let's Encrypt certificate.

The wait is controlled by:

```text
PUBLIC_READY_TIMEOUT=600
```

Allowed wizard range: `30`–`3600` seconds.

If certificate issuance fails after DNS is ready, check:

```text
TCP 80 forwarding
TCP 443 forwarding
SERVER_LAN_IP
Cloudflare token permissions
CGNAT/public reachability
```

HTTP-01 requires TCP 80 during the install.

## Strict Acceptance

The post-deploy test is:

```bash
python3 scripts/acceptance.py
```

It retries until `PUBLIC_READY_TIMEOUT` and requires:

- every Compose service in the `all` profile to be running;
- healthchecked containers to be healthy;
- expected LAN service ports to be open;
- public non-LAN-only hostnames to resolve;
- TLS hostname/certificate validation to succeed;
- NPM routes to return non-5xx responses;
- the Headscale `/admin` OAuth path to be reachable.

A failed acceptance returns a non-zero exit code. The Windows wizard treats that as deployment failure and does not show a green completion state.

## Domains

`BASE_DOMAIN` supplies defaults, while every service may use an explicit FQDN override.

Example:

```text
BASE_DOMAIN=mydomain.net
AIOSTREAMS_HOST=aio.example.org
AIOMETADATA_HOST=metadata.example.org
MEDIAFLOW_HOST=proxy.example.net
EASYPROXY_HOST=easyproxy.example.net
HEADSCALE_HOST=mesh.example.org
STREAMVIX_HOST=vix.example.org
TVVOO_HOST=tv.example.org
AIOMANAGER_HOST=manager.example.org
SEANIME_HOST=anime.example.org
SEANIME_SHARED_HOST=anime-shared.example.org
COMETNET_HOST=cometnet.example.org
STREMTHRU_HOST=stremthru.example.org
PORTAINER_HOST=docker.example.org
```

The selected hostnames are propagated to application URLs, OAuth, Cloudflare DDNS, certificates and NPM.

## Runtime-generated keys

With:

```text
AUTO_RUNTIME_KEYS=true
```

the setup attempts to obtain automatically:

- Jackett API key;
- Headscale user;
- Headscale API key;
- Headscale pre-auth key for Tailscale.

Disable deliberately with:

```bash
./setup.sh --no-runtime-keys
```

and provide the missing values yourself.

## Nginx Proxy Manager

Relevant settings:

```text
NPM_ADMIN_EMAIL=
NPM_ADMIN_PASSWORD=
LETSENCRYPT_EMAIL=
AUTO_CONFIGURE_NPM=true
PUBLIC_READY_TIMEOUT=600
```

The setup:

1. updates Cloudflare DDNS for the selected hosts;
2. starts DDNS and NPM;
3. waits for public DNS visibility;
4. authenticates to the NPM API;
5. reuses or requests one shared SAN certificate;
6. creates/updates the current public and LAN-only proxy hosts;
7. applies Headscale/OAuth2/Headplane routing;
8. verifies that all required host objects exist.

The NPM apply step is idempotent and does not delete unrelated manual hosts.

Skip it with:

```bash
./setup.sh --no-npm
```

or:

```text
AUTO_CONFIGURE_NPM=false
```

## Rerunning

`setup.sh` always renders from tracked templates using the current `setup.env` and reconciles NPM again. Existing matching hosts are updated in place.

Application databases and personal state are not copied or published by rerunning the installer.

## AIOStreams

The wizard configures the AIOStreams bootstrap `.env` and shared credentials. Runtime configuration still lives in AIOStreams' own state/database.

Import a sanitized AIOStreams JSON export after the service is running, then add private provider/indexer/Usenet/debrid credentials locally.

## Remaining first-run application state

After `ACCEPTANCE OK`, infrastructure/DNS/TLS/routing are ready. The remaining operator-specific state is intentionally manual:

- Jackett indexers/account state;
- AIOStreams sanitized JSON import and private credentials;
- optional user-specific state in Seanime/Portainer or other apps.

AdGuard Home is outside this Compose and should be configured as a separate LAN resolver if used.
