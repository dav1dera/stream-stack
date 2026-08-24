# Nginx Proxy Manager — automated reference routing

This repository treats Nginx Proxy Manager as **desired state**, not as a database that must be copied from another installation.

The normal installation path is simply:

```bash
./setup.sh
```

After the main renderer has created the runtime files, `scripts/npm_apply.py` starts Cloudflare DDNS and Nginx Proxy Manager, logs into the NPM API, obtains/reuses a shared Let's Encrypt certificate and creates or updates the proxy hosts below.

No NPM SQLite database, certificate private key or previous installation state is shipped in Git.

## Hostnames are not hardcoded

The reference topology is fixed, but the **public names are not**.

`BASE_DOMAIN` only supplies convenient defaults. For example, with:

```text
BASE_DOMAIN=mydomain.net
```

the wizard derives names such as `aiostreams.mydomain.net`, `headscale.mydomain.net`, etc.

Every public service can instead use a completely different FQDN in `setup.env`:

```text
AIOSTREAMS_HOST=aio.media.example
MEDIAFLOW_HOST=proxy.example.net
HEADSCALE_HOST=mesh.example.org
SEANIME_HOST=anime.home.example
```

Those overrides are propagated to the service configs, OAuth callback/whitelist values, Honey links, Cloudflare DDNS and NPM. They may use different Cloudflare zones as long as the supplied API token has DNS edit access to those zones.

The DDNS renderer preserves the reference wildcard record for `*.BASE_DOMAIN` **and** explicitly manages every selected public hostname. This avoids an old/stale explicit DNS record shadowing the wildcard.

## NPM administrator

On a fresh NPM database, the wizard injects the supported initial-admin environment variables before the first NPM start.

The relevant one-file settings are:

```text
NPM_ADMIN_EMAIL=
NPM_ADMIN_PASSWORD=
LETSENCRYPT_EMAIL=
AUTO_CONFIGURE_NPM=true
```

Defaults:

- blank `NPM_ADMIN_EMAIL` -> `ALLOWED_EMAIL`;
- blank `NPM_ADMIN_PASSWORD` -> a strong locally generated password;
- blank `LETSENCRYPT_EMAIL` -> `ALLOWED_EMAIL`.

The resolved password is stored only in the gitignored `setup.env` and generated `data/npm/.env`.

If the NPM database already exists, `INITIAL_ADMIN_*` deliberately does **not** overwrite the existing account. Put the current NPM login into `setup.env` and rerun `./setup.sh`.

## Reference proxy topology

The wizard reproduces the same forwarding logic as the reference private deployment:

| Setup setting | Forward scheme | Forward target | Port | WebSocket |
|---|---|---|---:|---:|
| `AIOSTREAMS_HOST` | `http` | `aiostreams` | 4444 | no |
| `AIOMETADATA_HOST` | `http` | `aiometadata` | 1337 | yes |
| `MEDIAFLOW_HOST` | `http` | `mediaflow-proxy-light` | 8888 | no |
| `HEADSCALE_HOST` | `http` | `headscale` | 8080 | yes |
| `PORTAINER_HOST` | `http` | `portainer` | 9000 | no |
| `STREMTHRU_HOST` | `http` | `gluetun` | 9090 | no |
| `SEANIME_HOST` | `http` | `gluetun` | 43211 | yes |
| `SEANIME_SHARED_HOST` | `http` | `gluetun` | 43311 | yes |
| `COMETNET_HOST` | `http` | `gluetun` | 8765 | yes |
| `STREAMVIX_HOST` | `http` | `gluetun` | 7860 | no |

For every managed host the wizard applies:

- SSL certificate assigned;
- Force SSL = on;
- HTTP/2 = on;
- HSTS = on;
- HSTS subdomains = on;
- Block Common Exploits = on;
- caching = off;
- WebSocket support exactly as shown above.

`Comet` itself stays LAN/internal on port `2020`; AIOStreams reaches it internally as `http://gluetun:2020`, matching the reference architecture.

## Shared certificate

The wizard uses **one shared Let's Encrypt certificate** for the actual selected public hostnames.

It intentionally requests exact SAN names instead of assuming `*.example.com`. This keeps the same single-certificate logic while also supporting installers who choose arbitrary labels or hostnames in different zones.

Cloudflare DDNS is started before NPM requests the certificate, and the reference setting remains `PROXIED=false`, so HTTP-01 validation can reach NPM on forwarded TCP port 80.

Before running the installer, the router must forward TCP 80/443 to the Docker host and the Cloudflare API token must be able to create/update the selected DNS records.

If DNS has not propagated yet, certificate issuance can fail. Nothing is lost: fix DNS/port forwarding and rerun `./setup.sh`. Existing proxy hosts/certificates are discovered and reused where possible.

## Headscale + Headplane + OAuth2 Proxy

This is the only proxy host with special advanced routing.

The public value of `HEADSCALE_HOST` serves two applications on one hostname:

- `/` -> Headscale (`headscale:8080`);
- `/admin` -> OAuth2 Proxy -> Headplane;
- `/oauth2/` -> OAuth2 Proxy;
- `/oauth2/callback` -> OAuth2 Proxy with the same unauthorized-login behavior as the reference server.

The wizard generates the Advanced Nginx block dynamically from the chosen `HEADSCALE_HOST`; there is no hardcoded domain in it.

Equivalent generated logic:

```nginx
location = /admin/logout.data {
    add_header X-Remix-Redirect "https://<HEADSCALE_HOST>/oauth2/sign_in?rd=%2Fadmin" always;
    add_header X-Remix-Reload-Document "true" always;
    return 204;
}

location = /oauth2/callback {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;

    proxy_intercept_errors on;
    error_page 403 =302 /oauth2/sign_in?rd=%2Fadmin;

    proxy_pass http://oauth2-proxy:4180;
}

location /oauth2/ {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}

location /admin {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}
```

Headplane's own OIDC block stays disabled; OAuth2 Proxy remains the authentication layer, matching the reference deployment.

## Idempotency / reruns

`npm_apply.py` does not blindly create duplicates.

On every run it:

1. resolves the selected hostname for every managed service;
2. logs into the local NPM API;
3. searches existing Let's Encrypt certificates for one covering all selected hosts;
4. reuses it when possible or creates a new shared certificate;
5. searches existing proxy hosts by domain name;
6. updates matching hosts in place or creates missing ones;
7. verifies that every required hostname is present afterward.

Unrelated/manual NPM proxy hosts are left untouched.

For inspection, the resolved non-secret desired state is written locally to:

```text
data/npm/stream-stack-hosts.json
```

That file is gitignored.

## Disable NPM automation

For debugging or an existing NPM installation you do not want the wizard to alter:

```bash
./setup.sh --no-npm
```

or set:

```text
AUTO_CONFIGURE_NPM=false
```

Then use the topology table and Headscale Advanced block above as the manual equivalent.

## Verification

After `./setup.sh` succeeds:

```bash
curl -I "https://$(grep '^AIOSTREAMS_HOST=' setup.env | cut -d= -f2-)"
curl -I "https://$(grep '^MEDIAFLOW_HOST=' setup.env | cut -d= -f2-)"
curl -I "https://$(grep '^HEADSCALE_HOST=' setup.env | cut -d= -f2-)"
```

Also open `<HEADSCALE_HOST>/admin` in a browser. With no valid OAuth session it should enter the OAuth2 Proxy/Google login flow, while normal Headscale traffic continues to use `/`.
