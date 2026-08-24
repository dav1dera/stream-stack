# stream-stack

Sanitized and reproducible version of the reference Docker streaming stack.

The objective is **not merely to make the containers start**. A fresh Ubuntu host should be able to reach the same architecture and behavior as the reference deployment using the new operator's own domains, accounts, API keys, indexers and provider credentials.

Private databases and identity state are deliberately not published. They are rebuilt locally during first run.

## What this repository reproduces

The repository preserves the 29-service Docker Compose topology, fixed Docker networks, PostgreSQL/PgBouncer/Redis layout, Gluetun + WARP/GOST proxy chain, Headscale/Tailscale/Headplane/OAuth2 architecture, AdGuard -> DNSCrypt path, Nginx Proxy Manager routing, AIOStreams bootstrap/tuning, Comet/CometNet, StremThru, StreamViX, MediaFlow Proxy Light, AIOMetadata, two Seanime instances, Honey, Jackett, Portainer, TeamSpeak, Watchtower and Deunhealth.

It intentionally does **not** publish application databases, NPM/Portainer state, certificates, Headscale/Tailscale/WARP identities, Jackett indexer logins, Seanime libraries, Comet caches, AdGuard runtime state, AIOStreams runtime DB, Usenet credentials or third-party secrets.

---

# 1. Prepare the host

Reference target: **Ubuntu Server 24.04 LTS**, Docker Engine and Docker Compose v2.

Prepare:

- a static/DHCP-reserved LAN IP for the Docker host;
- `/dev/net/tun`;
- TCP 80/443 forwarded from the router to the Docker host for public HTTPS;
- TCP/UDP 53 free for AdGuard Home;
- a public domain, with Cloudflare DNS/DDNS in the reference architecture;
- free Docker ranges `172.18.0.0/24` and `172.19.0.0/24`.

Check that the Docker networks do not overlap your LAN/VPN:

```bash
ip route
ip addr
```

If they conflict, change the Compose subnets and corresponding fixed IP references **before first start**.

Enable forwarding for the Headscale subnet-router/exit-node role:

```bash
cat <<'EOF_SYSCTL' | sudo tee /etc/sysctl.d/99-stream-stack.conf
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF_SYSCTL
sudo sysctl --system
```

## Free DNS port 53

The reference host lets AdGuard own TCP/UDP 53 instead of `systemd-resolved`:

```bash
sudo systemctl disable --now systemd-resolved
sudo rm -f /etc/resolv.conf
printf 'nameserver 1.1.1.1\nnameserver 9.9.9.9\n' | sudo tee /etc/resolv.conf
sudo chmod 644 /etc/resolv.conf
sudo ss -lntup | grep ':53 ' || true
```

The final command should not show another listener on port 53.

---

# 2. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl python3
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"${UBUNTU_CODENAME:-$VERSION_CODENAME}\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out/in or reboot, then verify:

```bash
docker version
docker compose version
docker run --rm hello-world
```

---

# 3. Configure the whole repository once

The normal installation path does **not** require editing service files one by one.

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
./setup.sh
```

`setup.sh` is the primary configuration tool. It creates a local, gitignored `setup.env`, asks for missing installation-specific values and renders the actual runtime files from the public `*.example` templates.

It automatically:

- creates all `.env`, `config.yaml`, `config.toml`, `config.json`, PgBouncer user-list and OAuth allow-list files;
- creates all required bind-mount directories;
- derives normal service hostnames from one `BASE_DOMAIN`;
- accepts full per-service hostname overrides when different names are wanted;
- applies the same LAN IP/subnet everywhere;
- generates strong local-only secrets where possible;
- keeps shared credentials identical across every service that consumes them;
- gives the two Seanime instances separate generated passwords;
- checks active files for unresolved `CHANGE_ME_*`, `example.com` and example-LAN values;
- runs `docker compose config --quiet`;
- optionally starts Gluetun, Headscale and Jackett to obtain runtime-generated keys;
- starts Cloudflare DDNS + Nginx Proxy Manager;
- creates/reuses the NPM administrator and Let's Encrypt certificate;
- creates or updates the reference NPM proxy-host topology automatically.

Detailed behavior is documented in **[docs/SETUP.md](docs/SETUP.md)**.

## Alternative: fill one file yourself

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
```

Do **not** commit `setup.env`. It contains secrets and is ignored by Git.

### Values you normally provide

The important operator inputs are:

- `BASE_DOMAIN`
- `SERVER_LAN_IP`
- `LAN_SUBNET`
- `ALLOWED_EMAIL`
- Cloudflare API token
- Mullvad/WireGuard private key + tunnel CIDR
- TMDB API key + read token
- TVDB API key
- TorBox API key
- Google OAuth client ID + secret

Optional integrations such as MDBList, Gemini, AniList, Trakt and the StremThru GitHub integration can be left blank when deliberately unused.

### Domains are fully configurable

The reference names are only defaults.

With:

```text
BASE_DOMAIN=mydomain.net
```

the wizard derives names such as:

```text
aiostreams.mydomain.net
mfp.mydomain.net
headscale.mydomain.net
seanime.mydomain.net
```

Every public service also has an optional full-FQDN override:

```text
AIOSTREAMS_HOST=aio.example.org
MEDIAFLOW_HOST=proxy.example.net
HEADSCALE_HOST=mesh.example.com
SEANIME_HOST=anime.example.net
```

The labels do not need to match the reference names. Hostnames may even belong to different Cloudflare zones if the supplied token can edit those zones.

Those choices are propagated to application URLs, OAuth callbacks/whitelists, Headscale/Headplane, Honey, Cloudflare DDNS, Let's Encrypt and NPM. There is no hardcoded `example.com` assumption in the active configuration path.

### Values generated automatically when blank

Examples include:

- PostgreSQL password;
- AIOStreams `SECRET_KEY`, operator password and config-access key;
- AIOMetadata admin/addon passwords;
- Comet admin/config/API/stream-proxy credentials;
- MediaFlow password;
- Headplane/OAuth2 cookie secrets;
- StremThru password/vault secret;
- both Seanime passwords;
- Nginx Proxy Manager admin password.

The generated values are written back to local `setup.env` with mode `0600`.

### Runtime-generated Jackett / Headscale values

A fresh Jackett API key and fresh Headscale API/pre-auth keys do not exist until those applications have run.

With the default:

```text
AUTO_RUNTIME_KEYS=true
```

`setup.sh` starts only `gluetun`, `headscale` and `jackett`, then attempts to:

- read Jackett's generated API key;
- create the configured Headscale user;
- generate the Headscale API key used by Headplane;
- generate the Headscale pre-auth key used by the Tailscale container;
- rerender the affected files automatically.

If that bootstrap cannot be completed, the wizard lists the remaining value. Put it in `setup.env` and rerun `./setup.sh`.

---

# 4. Values synchronized automatically

The wizard deliberately uses a single source of truth for shared values.

| Value | Consumers |
|---|---|
| PostgreSQL password | PostgreSQL, PgBouncer, PgBouncer userlist, Comet, CometNet, StremThru |
| AIO operator login | AIOStreams auth, permissions and forced native-service credential |
| Comet public token | Comet, CometNet and AIOStreams Comet integration |
| Jackett API key | AIOStreams + Comet |
| MediaFlow password | MediaFlow + StreamViX |
| TorBox key | AIOStreams + Comet |
| Google OAuth client | OAuth2 Proxy and related Headplane template values |
| Headscale hostname | Headscale, Headplane, OAuth2 Proxy, Tailscale and NPM |
| Server LAN IP/subnet | Headscale, Tailscale, Honey and relevant generated config |
| Service hostnames | application config, Cloudflare DDNS, NPM and HTTPS certificate |

You should not need to synchronize these file-by-file.

---

# 5. Database and proxy foundation

`setup.sh` may already have started some bootstrap services. Confirm the database layer:

```bash
docker compose --profile db up -d postgres redis pgbouncer
docker compose ps postgres redis pgbouncer
docker exec postgres pg_isready -U postgres
docker exec pgbouncer pg_isready -h 127.0.0.1 -p 6432 -U postgres
```

On an empty `pgdata`, the supplied init SQL creates empty `comet` and `stremthru` databases.

Start/confirm the proxy chain:

```bash
docker compose up -d gluetun microwarp gost
docker inspect --format '{{.State.Health.Status}}' gluetun
```

Do not continue until Gluetun is `healthy`.

Reference proxy endpoints:

- `socks5h://gluetun:1081`
- `http://gluetun:8889`
- `socks5h://warp:1080`
- `http://gost:8082`

MicroWARP creates a fresh identity in `warp-data`; do not copy another installation's WARP state.

---

# 6. Public DNS + Nginx Proxy Manager

This stage is part of `./setup.sh` by default.

The wizard:

1. keeps the wildcard `*.BASE_DOMAIN` DDNS behavior of the reference deployment;
2. also adds every selected public hostname explicitly to Cloudflare DDNS;
3. starts `cloudflare-ddns` and `npm`;
4. creates the NPM initial admin automatically on a fresh database;
5. authenticates to the NPM API;
6. reuses a suitable existing Let's Encrypt certificate or requests one shared SAN certificate for all selected public hostnames;
7. creates or updates the proxy hosts below;
8. verifies the required domains exist in NPM.

NPM is therefore **not** a manual file-by-file or host-by-host setup anymore.

Reference forwarding logic:

| Setup setting | Forward target | WebSocket |
|---|---|---:|
| `AIOSTREAMS_HOST` | `aiostreams:4444` | no |
| `AIOMETADATA_HOST` | `aiometadata:1337` | yes |
| `MEDIAFLOW_HOST` | `mediaflow-proxy-light:8888` | no |
| `HEADSCALE_HOST` | `headscale:8080` | yes |
| `PORTAINER_HOST` | `portainer:9000` | no |
| `STREMTHRU_HOST` | `gluetun:9090` | no |
| `SEANIME_HOST` | `gluetun:43211` | yes |
| `SEANIME_SHARED_HOST` | `gluetun:43311` | yes |
| `COMETNET_HOST` | `gluetun:8765` | yes |
| `STREAMVIX_HOST` | `gluetun:7860` | no |

For all managed hosts the reference security/transport logic is retained: HTTPS certificate assigned, Force SSL, HTTP/2, HSTS + subdomains and Block Common Exploits enabled; caching remains disabled; WebSocket is enabled only where required.

The Headscale hostname also receives the special `/admin` and `/oauth2/` locations that route through OAuth2 Proxy to Headplane. Those locations are generated using the actual selected `HEADSCALE_HOST`.

See **[docs/NPM.md](docs/NPM.md)** for the exact desired state and manual fallback.

To prevent the wizard from touching NPM:

```bash
./setup.sh --no-npm
```

or set:

```text
AUTO_CONFIGURE_NPM=false
```

---

# 7. Headscale + OAuth2 Proxy + Tailscale

If automatic runtime-key bootstrap succeeded, `setup.env` already contains the fresh Headscale API key and pre-auth key and the generated Headplane/Tailscale runtime files already contain them.

Confirm the Headscale state:

```bash
docker compose up -d headscale
docker exec -it headscale headscale users list
```

If automatic generation was disabled or failed, the equivalent manual commands are:

```bash
docker exec -it headscale headscale users create admin
docker exec -it headscale headscale users list
docker exec -it headscale headscale apikeys create --expiration 999d
docker exec -it headscale headscale preauthkeys create --user USER_ID --expiration 24h
```

Put manually generated values in `setup.env`, **not directly in multiple service files**, then rerun:

```bash
./setup.sh
```

The Headscale configuration uses sequential `100.64.0.0/10` allocation and MagicDNS. If the server is the first node it will normally receive `100.64.0.1`, which is the reference DNS address in the template.

Create the Google OAuth client using the actual selected Headscale hostname:

```text
https://<HEADSCALE_HOST>/oauth2/callback
```

The wizard writes its client ID/secret and allowed email into OAuth2 Proxy.

Start/confirm:

```bash
docker compose up -d headplane oauth2-proxy tailscale
docker exec -it headscale headscale nodes list
```

Open `https://<HEADSCALE_HOST>/admin`, authenticate, then approve subnet-route/exit-node capability when required.

---

# 8. DNSCrypt + AdGuard Home

Start DNSCrypt:

```bash
docker compose up -d dnscrypt-proxy
```

The tracked configuration listens internally at `172.18.0.4:5353` and preserves the reference resolver/cache setup.

Start fresh AdGuard:

```bash
docker compose up -d adguardhome
```

Open the first-run wizard at:

```text
http://SERVER_LAN_IP:3010
```

The Compose mapping is `3010:3000` because a clean AdGuard container exposes the setup wizard internally on port 3000.

In the wizard set:

- web UI: `0.0.0.0:90`;
- DNS: `0.0.0.0:53`;
- upstream DNS: `172.18.0.4:5353`.

After setup, use `http://SERVER_LAN_IP:90`.

Only change the LAN/router DNS to `SERVER_LAN_IP` after:

```bash
dig @SERVER_LAN_IP cloudflare.com
dig @SERVER_LAN_IP github.com
```

If this server's Headscale address is not `100.64.0.1`, change `dns.nameservers.global` in the Headscale template/runtime config accordingly.

---

# 9. Start the full stack

```bash
docker compose --profile all up -d
docker compose --profile all ps
```

Do not continue while a required service is `restarting` or `unhealthy`.

---

# 10. Required first-run application state

The one-shot wizard removes **file-by-file configuration**, but it cannot safely publish or manufacture external accounts and application database state.

## Jackett

The API key is normally discovered automatically by `setup.sh`.

You still need to open:

```text
http://SERVER_LAN_IP:9117
```

and add **your own** torrent indexers. To mirror the reference behavior, keep caching enabled, TTL around `2100` seconds and max results per indexer around `1000`.

## AIOStreams

AIOStreams runtime settings live in its own database. The repository configures the bootstrap `.env`, local credentials and integrations shared with the rest of the stack.

For reproducing the reference runtime configuration, import your **sanitized AIOStreams JSON export with credentials removed**, then add the new installation's provider/indexer/Usenet credentials through AIOStreams.

This avoids publishing the AIOStreams DB or secrets.

`docs/AIOSTREAMS.md` remains the behavioral reference for the four variants and expected filtering/failover behavior.

## MediaFlow Proxy Light

Its password is generated once and propagated automatically to StreamViX. If the AIOStreams JSON references MediaFlow credentials, use the same value stored in `setup.env`.

## StreamViX

The tracked template preserves both-link mode, AnimeUnity + AnimeSaturn enabled, WARP SOCKS5 primary proxy, GOST/WARP HTTP fallback and MediaFlow integration.

## Comet + CometNet

The tracked templates preserve scraper modes, cache TTLs, queue thresholds, workers, PostgreSQL/PgBouncer integration and CometNet bootstrap peers.

Comet itself remains LAN/internal on port `2020`; AIOStreams reaches it through `http://gluetun:2020`.

## StremThru

The template preserves port 9090, PostgreSQL, Redis and the Gluetun namespace. The wizard generates the local login/vault secret; add a minimally scoped GitHub token only if that integration is desired.

## AIOMetadata

The template preserves Redis, SOCKS routing, cache warming and MAL warming. Third-party API/OAuth credentials come from `setup.env`.

After creating the desired AIOMetadata configuration, put its UUID in:

```text
AIOMETADATA_CONFIG_UUID=
```

inside `setup.env` and rerun `./setup.sh`.

## Seanime main + shared

The wizard generates both config files and separate passwords:

- main -> port `43211`;
- shared -> port `43311`.

Libraries/databases/download state remain local and are intentionally not published.

## Honey

Honey is rendered automatically from the chosen public hostnames plus `SERVER_LAN_IP`, `PROXMOX_IP` and `AMP_IP`.

## Portainer

Open `http://SERVER_LAN_IP:9000`, create the new admin account and select the local Docker environment through the mounted Docker socket.

## TeamSpeak 6

Inspect first-start logs for its initial privilege/setup token:

```bash
docker logs teamspeak
```

Watchtower and Deunhealth require no UI setup; the tracked values preserve the reference Watchtower schedule and health-based restart behavior.

---

# 11. End-to-end verification

## No unresolved template values

```bash
grep -RIn --exclude='*.example' 'CHANGE_ME_' data || true
grep -RIn --exclude='*.example' 'example\.com' data || true
```

Both should be empty in active runtime files. `./setup.sh` performs the same class of check automatically.

## Compose / containers

```bash
docker compose config --quiet
docker compose --profile all ps
```

## Databases

```bash
docker exec postgres psql -U postgres -Atc "SELECT datname FROM pg_database WHERE datname IN ('comet','stremthru') ORDER BY datname;"
```

Expected: `comet` and `stremthru`.

## VPN

```bash
docker inspect --format '{{.State.Health.Status}}' gluetun
docker exec gluetun wget -qO- https://ipinfo.io/ip || true
```

## DNS

```bash
dig @SERVER_LAN_IP cloudflare.com
dig @SERVER_LAN_IP github.com
```

## Headscale

```bash
docker exec -it headscale headscale users list
docker exec -it headscale headscale nodes list
```

## NPM / HTTPS

Inspect the locally generated non-secret desired state:

```bash
cat data/npm/stream-stack-hosts.json
```

Verify the selected public hosts for AIOStreams, AIOMetadata, MediaFlow, Headscale/Headplane, StreamViX, both Seanime instances, StremThru and CometNet.

The deployment is not considered reproduced if the Headscale hostname serves Headscale on `/` but fails to send `/admin` through OAuth2 Proxy to Headplane.

## Streaming behavior

The deployment is not considered reproduced until AIOStreams succeeds for:

- a normal movie;
- a normal series episode;
- an anime episode;
- TorBox/debrid;
- Usenet;
- MediaFlow;
- Comet;
- StremThru;
- every intended AIOStreams profile/variant.

---

# 12. 29-service completion checklist

- [ ] tailscale
- [ ] portainer
- [ ] adguardhome
- [ ] dnscrypt-proxy
- [ ] headscale
- [ ] headplane
- [ ] npm
- [ ] cloudflare-ddns
- [ ] aiometadata
- [ ] mediaflow-proxy-light
- [ ] aiostreams
- [ ] pgbouncer
- [ ] postgres
- [ ] redis
- [ ] watchtower
- [ ] honey
- [ ] teamspeak
- [ ] microwarp
- [ ] gost
- [ ] oauth2-proxy
- [ ] deunhealth
- [ ] gluetun
- [ ] streamvix
- [ ] comet
- [ ] cometnet
- [ ] stremthru
- [ ] jackett
- [ ] seanime
- [ ] seanime-shared

---

# 13. Reset / backup semantics

Recreating a container is normally safe; deleting its persistent directory or named volume is not.

In particular, deleting `pgdata`, `warp-data`, Headscale `data/lib`, AIOStreams `data`, NPM `data` or Seanime data resets that application's state.

Back up private runtime state separately. Never add those backups to this public repository.

# Security check before every public push

`setup.env` and all rendered runtime files are ignored, but still review the repository before publishing:

```bash
git grep -nE '(ghp_|github_pat_|GOCSPX-|AIza|WIREGUARD_PRIVATE_KEY=[^C]|API_TOKEN=[^C]|PASSWORD=[^C])' || true
git status --ignored
```

Public Git should contain only templates, scripts and documentation — never generated credentials or databases.
