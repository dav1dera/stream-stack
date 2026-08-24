# stream-stack

Sanitized, reproducible version of the Docker stack. This repository intentionally contains **configuration only**.

It does **not** contain application databases, SQLite files, PostgreSQL/Redis data, Nginx Proxy Manager state/certificates, Portainer state, Tailscale/WARP identity state, Jackett indexer credentials, Seanime libraries/config databases, AIOStreams runtime database, Comet database/cache, AdGuard runtime state, or other persistent secrets.

## First install

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

The bootstrap script copies every tracked `*.example` template to the real untracked file used by Docker Compose. **Never commit the generated `.env`, `config.yaml`, `userlist.txt`, or `allowed-emails.txt` files.**

Before starting the stack, replace every `CHANGE_ME_*` value and every `example.com` / example LAN value listed below.

Then validate and start:

```bash
docker compose config
docker compose --profile all up -d
```

## Database password consistency

Use the **same PostgreSQL password** in all of these places:

- `data/postgres/.env`
- `data/pgbouncer/.env`
- `data/pgbouncer/data/userlist.txt`
- `data/comet/.env` (`DATABASE_URL`)
- `data/cometnet/.env` (`DATABASE_URL`)
- `data/stremthru/.env` (`STREMTHRU_DATABASE_URI`)

The first boot creates only the empty `comet` and `stremthru` databases from `data/postgres/init/01-databases.sql`. No database content from the private repository is transferred.

## Runtime-configured services

Some services intentionally start clean and must be configured from their own UI because their important settings live in a database or runtime state rather than a safe text config:

- **AIOStreams:** only bootstrap/env overrides are included. The AIOStreams runtime DB is not copied.
- **Nginx Proxy Manager:** proxy hosts, certificates, users and SQLite state are not copied.
- **Portainer:** Portainer state is not copied.
- **AdGuard Home:** runtime config/state is not copied; complete the first-run UI.
- **Jackett:** indexer definitions/API state are not copied; configure indexers again and paste the new API key into AIOStreams/Comet.
- **Seanime:** libraries, downloads, cache and user databases are not copied.
- **Honey:** dashboard state/config is not copied.
- **Tailscale / Headscale:** node state/private keys are not copied.
- **MicroWARP:** WireGuard/WARP identity volume is not copied.
- **Comet / CometNet:** PostgreSQL data, generated node keys/pools and caches are not copied.

## Exact values to edit

The line numbers below refer to the tracked `*.example` files in this repository. After `./scripts/bootstrap.sh`, edit the corresponding real file with the same line number.

| File | Line | Value to replace |
|---|---:|---|
| `data/aiometadata/.env.example` | 2 | `HOST_NAME=https://aiometadata.example.com` |
| `data/aiometadata/.env.example` | 9 | `ADMIN_KEY=CHANGE_ME_AIOMETADATA_ADMIN_KEY` |
| `data/aiometadata/.env.example` | 10 | `ADDON_PASSWORD=CHANGE_ME_AIOMETADATA_ADDON_PASSWORD` |
| `data/aiometadata/.env.example` | 12 | `TMDB_API=CHANGE_ME_TMDB_API_KEY` |
| `data/aiometadata/.env.example` | 13 | `TVDB_API_KEY=CHANGE_ME_TVDB_API_KEY` |
| `data/aiometadata/.env.example` | 16 | `MDBLIST_API_KEY=CHANGE_ME_MDBLIST_API_KEY` |
| `data/aiometadata/.env.example` | 17 | `GEMINI_API_KEY=CHANGE_ME_GEMINI_API_KEY` |
| `data/aiometadata/.env.example` | 19 | `ANILIST_CLIENT_ID=CHANGE_ME_ANILIST_CLIENT_ID` |
| `data/aiometadata/.env.example` | 20 | `ANILIST_CLIENT_SECRET=CHANGE_ME_ANILIST_CLIENT_SECRET` |
| `data/aiometadata/.env.example` | 21 | `ANILIST_REDIRECT_URI=https://aiometadata.example.com/anilist/callback` |
| `data/aiometadata/.env.example` | 23 | `TRAKT_CLIENT_ID=CHANGE_ME_TRAKT_CLIENT_ID` |
| `data/aiometadata/.env.example` | 24 | `TRAKT_CLIENT_SECRET=CHANGE_ME_TRAKT_CLIENT_SECRET` |
| `data/aiometadata/.env.example` | 25 | `TRAKT_REDIRECT_URI=https://aiometadata.example.com/api/auth/trakt/callback` |
| `data/aiometadata/.env.example` | 32 | `CACHE_WARMUP_UUIDS=CHANGE_ME_AIOMETADATA_CONFIG_UUID` |
| `data/aiostreams/.env.example` | 1 | `BASE_URL=https://aiostreams.example.com` |
| `data/aiostreams/.env.example` | 2 | `SECRET_KEY=CHANGE_ME_64_HEX_SECRET` |
| `data/aiostreams/.env.example` | 9 | `AIOSTREAMS_AUTH=CHANGE_ME_AIO_USER:CHANGE_ME_AIO_PASSWORD` |
| `data/aiostreams/.env.example` | 10 | `AIOSTREAMS_AUTH_PERMISSIONS=CHANGE_ME_AIO_USER=admin` |
| `data/aiostreams/.env.example` | 12 | `CONFIG_ACCESS_KEY=CHANGE_ME_AIO_CONFIG_ACCESS_KEY` |
| `data/aiostreams/.env.example` | 21 | `BUILTIN_JACKETT_API_KEY=CHANGE_ME_JACKETT_API_KEY` |
| `data/aiostreams/.env.example` | 26 | `TMDB_ACCESS_TOKEN=CHANGE_ME_TMDB_ACCESS_TOKEN` |
| `data/aiostreams/.env.example` | 27 | `TMDB_API_KEY=CHANGE_ME_TMDB_API_KEY` |
| `data/aiostreams/.env.example` | 28 | `TVDB_API_KEY=CHANGE_ME_TVDB_API_KEY` |
| `data/aiostreams/.env.example` | 31 | `TRUSTED_UUIDS=CHANGE_ME_AIO_TRUSTED_UUID` |
| `data/aiostreams/.env.example` | 47 | `COMET_PUBLIC_API_TOKEN=CHANGE_ME_COMET_PUBLIC_API_TOKEN` |
| `data/aiostreams/.env.example` | 50 | `FORCED_SERVICE_CREDENTIALS='torbox.apiKey=CHANGE_ME_TORBOX_API_KEY\naiostreams.aiostreamsAuth=CHANGE_ME_AIO_USER:CHANGE_ME_AIO_PASSWORD'` |
| `data/cloudflare-ddns/.env.example` | 1 | `CLOUDFLARE_API_TOKEN=CHANGE_ME_CLOUDFLARE_API_TOKEN` |
| `data/cloudflare-ddns/.env.example` | 2 | `DOMAINS=*.example.com` |
| `data/comet/.env.example` | 11 | `ADMIN_DASHBOARD_PASSWORD=CHANGE_ME_COMET_ADMIN_PASSWORD` |
| `data/comet/.env.example` | 13 | `CONFIGURE_PAGE_PASSWORD=CHANGE_ME_COMET_CONFIG_PASSWORD` |
| `data/comet/.env.example` | 15 | `PUBLIC_API_TOKEN=CHANGE_ME_COMET_PUBLIC_API_TOKEN` |
| `data/comet/.env.example` | 19 | `DATABASE_URL=postgres:CHANGE_ME_POSTGRES_PASSWORD@pgbouncer:6432/comet` |
| `data/comet/.env.example` | 57 | `JACKETT_API_KEY=CHANGE_ME_JACKETT_API_KEY` |
| `data/comet/.env.example` | 91 | `AIOSTREAMS_URL=https://aio.example.com` |
| `data/comet/.env.example` | 94 | `JACKETTIO_URL=https://jackettio.example.com` |
| `data/comet/.env.example` | 103 | `PROXY_DEBRID_STREAM_PASSWORD=CHANGE_ME_COMET_STREAM_PROXY_PASSWORD` |
| `data/comet/.env.example` | 106 | `PROXY_DEBRID_STREAM_DEBRID_DEFAULT_APIKEY=CHANGE_ME_TORBOX_API_KEY` |
| `data/comet/.env.example` | 112 | `COMETNET_API_KEY=CHANGE_ME_COMETNET_API_KEY` |
| `data/cometnet/.env.example` | 1 | `COMETNET_API_KEY=CHANGE_ME_COMETNET_API_KEY` |
| `data/cometnet/.env.example` | 3 | `COMETNET_ADVERTISE_URL=wss://cometnet.example.com/cometnet/ws` |
| `data/cometnet/.env.example` | 9 | `DATABASE_URL=postgres:CHANGE_ME_POSTGRES_PASSWORD@pgbouncer:6432/comet` |
| `data/gluetun/.env.example` | 3 | `WIREGUARD_PRIVATE_KEY=CHANGE_ME_WIREGUARD_PRIVATE_KEY` |
| `data/gluetun/.env.example` | 4 | `WIREGUARD_ADDRESSES=CHANGE_ME_WIREGUARD_ADDRESS_CIDR` |
| `data/headplane/data/config.yaml.example` | 4 | `base_url: "https://headscale.example.com"` |
| `data/headplane/data/config.yaml.example` | 5 | `cookie_secret: "CHANGE_ME_HEADPLANE_32_CHAR_SECRET"` |
| `data/headplane/data/config.yaml.example` | 17 | `url: "https://headscale.example.com"` |
| `data/headplane/data/config.yaml.example` | 18 | `api_key: "CHANGE_ME_HEADSCALE_API_KEY"` |
| `data/headplane/data/config.yaml.example` | 41 | `client_id: "CHANGE_ME_GOOGLE_OAUTH_CLIENT_ID"` |
| `data/headplane/data/config.yaml.example` | 42 | `client_secret: "CHANGE_ME_GOOGLE_OAUTH_CLIENT_SECRET"` |
| `data/headscale/data/config/config.yaml.example` | 1 | `server_url: https://headscale.example.com` |
| `data/headscale/data/config/config.yaml.example` | 66 | `base_domain: tailnet.example.com` |
| `data/headscale/data/config/config.yaml.example` | 70 | `- 192.168.1.10` |
| `data/headscale/data/config/config.yaml.example` | 74 | `- name: temp.tailnet.example.com` |
| `data/headcale/data/config/config.yaml.example` | 76 | `value: 192.168.1.10` |
| `data/mediaflow-proxy-light/.env.example` | 4 | `APP__AUTH__API_PASSWORD=CHANGE_ME_MEDIAFLOW_PASSWORD` |
| `data/npm/.env.example` | 6 | `# DB_POSTGRES_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD` |
| `data/oauth2-proxy/.env.example` | 2 | `OAUTH2_PROXY_CLIENT_ID=CHANGE_ME_GOOGLE_OAUTH_CLIENT_ID` |
| `data/oauth2-proxy/.env.example` | 3 | `OAUTH2_PROXY_CLIENT_SECRET=CHANGE_ME_GOOGLE_OAUTH_CLIENT_SECRET` |
| `data/oauth2-proxy/.env.example` | 4 | `OAUTH2_PROXY_REDIRECT_URL=https://headscale.example.com/oauth2/callback` |
| `data/oauth2-proxy/.env.example` | 9 | `OAUTH2_PROXY_COOKIE_SECRET=CHANGE_ME_32_BYTE_COOKIE_SECRET` |
| `data/oauth2-proxy/.env.example` | 21 | `OAUTH2_PROXY_WHITELIST_DOMAINS=headscale.example.com` |
| `data/oauth2-proxy/allowed-emails.txt.example` | 1 | `you@example.com` |
| `data/pgbouncer/.env.example` | 2 | `DB_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD` |
| `data/pgbouncer/data/userlist.txt.example` | 1 | `"postgres" "CHANGE_ME_POSTGRES_PASSWORD"` |
| `data/postgres/.env.example` | 2 | `POSTGRES_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD` |
| `data/streamvix/.env.example` | 2 | `MFP_URL=https://mfp.example.com` |
| `data/streamvix/.env.example` | 3 | `MFP_PSW=CHANGE_ME_MEDIAFLOW_PASSWORD` |
| `data/streamvix/.env.example` | 4 | `TMDB_API_KEY=CHANGE_ME_TMDB_API_KEY` |
| `data/streamvix/.env.example` | 5 | `ADDON_BASE_URL=https://streamv.example.com` |
| `data/stremthru/.env.example` | 6 | `STREMTHRU_AUTH=CHANGE_ME_STREMTHRU_USER:CHANGE_ME_STREMTHRU_PASSWORD` |
| `data/stremthru/.env.example` | 7 | `STREMTHRU_AUTH_ADMIN=CHANGE_ME_STREMTHRU_USER` |
| `data/stremthru/.env.example` | 8 | `STREMTHRU_VAULT_SECRET=CHANGE_ME_64_HEX_VAULT_SECRET` |
| `data/stremthru/.env.example` | 10 | `STREMTHRU_INTEGRATION_GITHBB_USER=CHANGE_ME_GITHUB_USERNAME` |
| `data/stremthru/.env.example` | 11 | `STREMTHRU_INTEGRATION_GITHUB_TOKEN=CHANGE_ME_GITHBB_TOKEN` |
| `data/stremthru/.env.example` | 13 | `STREMTHRU_DATABASE_URI=postgresql://postgres:CHANGE_ME_POSTGRES_PASSWORD@pgbouncer:6432/stremthru` |
| `data/tailscale/.env.example` | 2 | `TS_EXTRA_ARGS=--login-server=https://headscale.example.com --accept-dns=false --advertise-routes=192.168.1.0/24,172.18.0.0/24,172.19.0.0/24 --advertise-exit-node` |
| `data/tailscale/.env.example` | 4 | `TS_AUTHKEY=CHANGE_ME_HEADSCALE_AUTHKEY` |
| `scripts/bootstrap.sh` | 47 | `echo "Templates copied. Edit every CHANGE_ME_* value before starting the stack."` |
| `scripts/bootstrap.sh` | 48 | `echo "Run: grep -RIn --exclude='*.example' 'CHANGE_ME_' \"$ROOT/data\""` |


## Service notes

### Tailscale / Headscale
Create a new Headscale pre-auth key and put it in `data/tailscale/.env`. Replace the example Headscale domain and LAN subnet. Headscale will generate its SQLite DB and private keys on first start.

### Headplane / OAuth2 Proxy
Generate fresh Headplane cookie/session secrets and a fresh Headscale API key. If Google OAuth is used, create a new OAuth client and make the redirect URI match your public Headscale domain. Put allowed Google accounts in `data/oauth2-proxy/allowed-emails.txt`, one per line.

### Cloudflare DDNS
Create a Cloudflare API token with only the DNS permissions required for the zone, then replace the wildcard example domain.

### Gluetun
Insert your own WireGuard private key and assigned tunnel address. The proxy/listening/firewall tuning from the private stack is preserved.

### AIOStreams
Generate `SECRET_KEY with:

```bash
openssl rand -hex 32
```

Do not copy the old AIOStreams SQLite database into this repository. Recreate runtime settings from the dashboard. The template preserves the current proxy topology and built-in local service URLs.

### PgBouncer / PostgreSQL
Change the default database password everywhere listed in **Database password consistency**. The supplied PostgreSQL config preserves the main performance tuning from the private stack without shipping the database itself.

### Comet / CometNet
Use fresh dashboard/config/API secrets. Comet and CometNet must share the same `COMETNET_API_KEY`. If TorBox is used as the default debrid service, use your own TorBox API key.

### StremThru
Generate a new vault secret and credentials. If GitHub integration is needed, use a new fine-grained token with the minimum required repository access; do not reuse a broad classic PAT.

### AIOMetadata / StreamVix / MediaFlow
Use new API keys/passwords and replace public hostnames with your own reverse-proxy domains.

## Security rule

The public repository must contain only templates. Before every push, run:

```bash
git grep -nE '(ghp_|GOCSPX-|AIza|WIREGUARD_PRIVATE_KEY=[^C]|API_TOKEN=[^C]|PASSWORD=[^C])' || true
git status --ignored
```

Review any match manually before publishing.
