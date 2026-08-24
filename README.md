# stream-stack

Sanitized and reproducible version of the reference Docker streaming stack.

The objective of this repository is **not only to make the containers start**. Follow the procedure below in order and a fresh Ubuntu host can be brought to the same architecture and behavior as the reference deployment, using the new operator's own domains, passwords, API keys, Usenet/indexer accounts and service credentials.

Private databases and identity state are deliberately not shipped. They are rebuilt locally during first run.

## What this repository reproduces

It preserves the 29-service Docker Compose topology, fixed Docker networks, PostgreSQL/PgBouncer/Redis layout, Gluetun + WARP/GOST proxy chain, Headscale/Tailscale/Headplane/OAuth2 architecture, AdGuard -> DNSCrypt path, NPM routing, AIOStreams tuning, Comet/CometNet settings, StremThru, StreamViX, MediaFlow Proxy Light, AIOMetadata, two Seanime instances, Honey, Jackett, Portainer, TeamSpeak, Watchtower and Deunhealth.

It intentionally does **not** publish application databases, NPM/Portainer state, certificates, Headscale/Tailscale/WARP identities, generated keys, Jackett credentials/indexer logins, Seanime libraries, Comet caches, AdGuard runtime state or third-party credentials.

---

# 1. Prepare the host

Reference target: **Ubuntu Server 24.04 LTS**, Docker Engine and Docker Compose v2.

Before installing, prepare:

- a static/DHCP-reserved LAN IP for the Docker host;
- `/dev/net/tun`;
- TCP 80/443 forwarded from the router to the Docker host for public HTTPS;
- TCP/UDP 53 free for AdGuard Home;
- a public domain; the reference architecture uses Cloudflare DNS/DDNS;
- free local ranges `172.18.0.0/24` and `172.19.0.0/24`.

Check that the Docker subnets do not overlap your LAN/VPN:

```bash
ip route
ip addr
```

If they conflict, change the Compose subnets and every corresponding fixed IP/reference **before first start**.

Enable forwarding for the Headscale subnet router/exit node:

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
sudo apt-get install -y ca-certificates curl
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

# 3. Clone and bootstrap the templates

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

The script creates the untracked runtime copies used by Compose, including all `.env` files, PgBouncer user list, OAuth allow-list, Headscale/Headplane config, Honey config and both Seanime configs. It also creates every required bind-mount directory.

Never commit the generated `.env`, `config.yaml`, `config.toml`, `config.json`, `userlist.txt` or `allowed-emails.txt` files.

---

# 4. Decide installation-specific values once

Recommended public hostnames:

| Service | Hostname pattern |
|---|---|
| AIOStreams | `aiostreams.example.com` |
| AIOMetadata | `aiometadata.example.com` |
| MediaFlow | `mfp.example.com` |
| Headscale + Headplane | `headscale.example.com` |
| StreamViX | `streamv.example.com` |
| Seanime | `seanime.example.com` |
| Seanime Shared | `shared-seanime.example.com` |
| CometNet | `cometnet.example.com` |
| StremThru | `stremthru.example.com` |
| Portainer | `portainer.example.com` |

Useful secret generators:

```bash
# 32 bytes / 64 hex characters
openssl rand -hex 32

# exactly 32 printable characters, suitable for the cookie secrets in these templates
openssl rand -hex 16

# general strong password
openssl rand -base64 24
```

## Values that must match across services

| Value | Keep identical in |
|---|---|
| PostgreSQL password | Postgres `.env`, PgBouncer `.env`, PgBouncer `userlist.txt`, Comet DB URL, CometNet DB URL, StremThru DB URI |
| Comet/CometNet API token | Comet `PUBLIC_API_TOKEN`, Comet `COMETNET_API_KEY`, CometNet `COMETNET_API_KEY`, AIOStreams `COMET_PUBLIC_API_TOKEN`, AIOStreams Comet Torznab URL/API key |
| Jackett API key | Jackett-generated key -> AIOStreams `BUILTIN_JACKETT_API_KEY` + Comet `JACKETT_API_KEY` |
| MediaFlow password | MediaFlow `APP__AUTH__API_PASSWORD`, StreamViX `MFP_PSW`, AIOStreams MediaFlow proxy credential |
| TorBox key | AIOStreams TorBox/forced credentials + Comet default debrid proxy key |
| AIO operator login | AIO auth/permissions, forced native-service auth, Newznab native-service proxy auth |
| Headscale hostname | Headscale, Headplane, OAuth2 Proxy, Tailscale login server and NPM |

After editing generated runtime files, the following must return no literal placeholders:

```bash
grep -RIn --exclude='*.example' 'CHANGE_ME_' data || true
grep -RIn --exclude='*.example' 'example\.com' data || true
```

Optional integrations such as MDBList, Gemini, AniList or Trakt may be left empty only if you deliberately disable/not use them. Never leave the literal `CHANGE_ME_*` value in an active runtime config.

Run before starting containers:

```bash
docker compose config --quiet
```

---

# 5. Start database + proxy foundation first

```bash
docker compose --profile db up -d postgres redis pgbouncer
docker compose ps postgres redis pgbouncer
docker exec postgres pg_isready -U postgres
docker exec pgbouncer pg_isready -h 127.0.0.1 -p 6432 -U postgres
```

On an empty `pgdata` volume the supplied init file creates empty `comet` and `stremthru` databases.

Start the VPN/proxy chain:

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

MicroWARP creates a fresh identity in `warp-data`. Do not copy another installation's WARP state. A personal WARP+ license can be applied separately; the architecture also works with the newly generated free WARP identity.

---

# 6. Public DNS + Nginx Proxy Manager

Configure `data/cloudflare-ddns/.env` with your Cloudflare token/domain, then:

```bash
docker compose up -d cloudflare-ddns npm
```

Reference DDNS behavior is wildcard DNS, `PROXIED=false`, one-minute updates and IPv6 DDNS disabled.

Open NPM at:

```text
http://SERVER_LAN_IP:81
```

Create its new admin account/certificate state and then follow **[docs/NPM.md](docs/NPM.md)** completely. That file contains the exact in-stack reverse-proxy matrix and the Headscale/Headplane OAuth2 custom locations.

The important routing is:

| Public service | Forward target | WebSocket |
|---|---|---:|
| AIOStreams | `aiostreams:4444` | no |
| AIOMetadata | `aiometadata:1337` | yes |
| MediaFlow | `mediaflow-proxy-light:8888` | no |
| Headscale | `headscale:8080` | yes |
| Headplane `/admin` | `oauth2-proxy:4180` | yes |
| Portainer | `portainer:9000` | no |
| StremThru | `gluetun:9090` | no |
| Seanime | `gluetun:43211` | yes |
| Seanime Shared | `gluetun:43311` | yes |
| CometNet | `gluetun:8765` | yes |
| StreamViX | `gluetun:7860` | no |

Use HTTPS/Let's Encrypt, Force SSL, HSTS and Block Common Exploits as documented in `docs/NPM.md`.

---

# 7. Bootstrap Headscale before Tailscale/Headplane

Start Headscale:

```bash
docker compose up -d headscale
```

Create the first user:

```bash
docker exec -it headscale headscale users create admin
docker exec -it headscale headscale users list
```

Generate a fresh API key for Headplane:

```bash
docker exec -it headscale headscale apikeys create --expiration 999d
```

Paste it into `data/headplane/data/config.yaml` -> `headscale.api_key`.

Generate the server Tailscale node pre-auth key using the user identifier shown by `users list`:

```bash
docker exec -it headscale headscale preauthkeys create --user USER_ID --expiration 24h
```

Paste it into `data/tailscale/.env` -> `TS_AUTHKEY`.

The Headscale template uses sequential `100.64.0.0/10` allocation. If the server is the first node it normally receives `100.64.0.1`; that address is also the reference MagicDNS nameserver in the template.

---

# 8. Google OAuth2 + Headplane + Tailscale

Create a Google OAuth client with redirect URI:

```text
https://headscale.example.com/oauth2/callback
```

Put the new client ID/secret in `data/oauth2-proxy/.env`. Add allowed Google accounts, one per line, to:

```text
data/oauth2-proxy/allowed-emails.txt
```

Headplane's own OIDC block intentionally remains disabled: OAuth2 Proxy is the authentication layer. The fixed proxy-auth CIDR `172.18.0.20/32` corresponds to the OAuth2 Proxy container.

Start:

```bash
docker compose up -d headplane oauth2-proxy tailscale
docker exec -it headscale headscale nodes list
```

Open `https://headscale.example.com/admin`, authenticate and approve the server's advertised subnet routes/exit-node capability in Headplane when required.

In `data/tailscale/.env`, replace `192.168.1.0/24` with your real LAN subnet before starting Tailscale.

---

# 9. DNSCrypt + AdGuard Home

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

The Compose mapping is intentionally `3010:3000`, because a clean AdGuard container exposes its setup wizard on internal port 3000. In the wizard set:

- web UI: `0.0.0.0:90`;
- DNS: `0.0.0.0:53`;
- upstream DNS: `172.18.0.4:5353`.

After setup, use `http://SERVER_LAN_IP:90` and configure the LAN/router to hand out `SERVER_LAN_IP` as DNS **only after** these work:

```bash
dig @SERVER_LAN_IP cloudflare.com
dig @SERVER_LAN_IP github.com
```

Headscale clients use the tailnet address of this server as DNS. If it is not `100.64.0.1`, update `dns.nameservers.global` in the Headscale config and restart Headscale.

---

# 10. Start the full stack

```bash
docker compose --profile all up -d
docker compose --profile all ps
```

Do not proceed while a required service is `restarting` or `unhealthy`.

---

# 11. Required first-run application configuration

## Jackett

Open `http://SERVER_LAN_IP:9117`, add **your own** torrent indexers and copy the fresh Jackett API key into AIOStreams and Comet. Restart both after editing. To mirror the reference server keep Jackett caching enabled, TTL about `2100` seconds and max results per indexer `1000`.

## MediaFlow Proxy Light

The password must match MediaFlow, StreamViX and the AIOStreams MediaFlow stream-proxy configuration. Verify both LAN `:8888` and `https://mfp.example.com`.

## StreamViX

The tracked `.env` already preserves both-link mode, AnimeUnity + AnimeSaturn enabled, WARP SOCKS5 primary proxy, GOST/WARP HTTP fallback and MediaFlow integration. Replace only installation-specific URLs/credentials.

## Comet + CometNet

The tracked templates preserve scraper modes, cache TTLs, queue thresholds, workers, PostgreSQL/PgBouncer integration and the CometNet bootstrap peers. Ensure the shared API token relationship from section 4 is respected and NPM WebSocket support is enabled for CometNet.

Comet itself remains LAN/internal at port `2020`; AIOStreams reaches it as `http://gluetun:2020`.

## StremThru

The template preserves port 9090, PostgreSQL, Redis and the Gluetun namespace. Generate a new vault secret/login and use your own minimally scoped GitHub token if the integration is needed.

## AIOMetadata

Supply your own API/OAuth credentials. The template already preserves Redis, SOCKS routing, cache warming and MAL warming. After creating the desired AIOMetadata configuration, set its fresh UUID in `CACHE_WARMUP_UUIDS` and restart the service.

## AIOStreams — mandatory

A new AIOStreams database is empty, therefore having the container online is **not enough**. Follow **[docs/AIOSTREAMS.md](docs/AIOSTREAMS.md)** completely.

That guide was reconstructed from the current reference export and records the Tamtaro v3.1.3 base, synced SEL/regex sources, sorting, deduplication, result/size limits, MediaFlow behavior, Usenet/debrid failover, Newznab/Torznab presets and all four variants:

- Shared ENG — 50 Mbps, Italian priority with English fallback;
- Shared ITA — strict Italian, 50 Mbps;
- Shared JPN — Japanese audio **and Japanese subtitles**, 50 Mbps;
- `marga` — Italian/English behavior with 10 Mbps cap.

For native Usenet, configure your own NNTP provider credentials. Indexer/debrid/provider accounts are never copied from the private deployment.

## Seanime main + shared

`bootstrap.sh` now creates both real config files from tracked templates before first start:

- main -> port `43211`;
- shared -> port `43311`.

Set different strong passwords at line 27 of each corresponding `config.toml`. Their DB/library/cache/download state is deliberately local.

## Honey

The Honey dashboard layout is now tracked as a sanitized `config.json.example`. Replace server/Proxmox/AMP addresses and public hostnames, then the dashboard reproduces the reference service set.

## Portainer

Open `http://SERVER_LAN_IP:9000`, create a new admin account and select the local Docker environment through the mounted socket.

## TeamSpeak 6

Inspect first-start logs for its initial privilege/setup token:

```bash
docker logs teamspeak
```

Watchtower and Deunhealth require no UI configuration; the tracked values preserve the 04:00 Watchtower schedule and health-based restart labels.

---

# 12. End-to-end verification

## Placeholders

```bash
grep -RIn --exclude='*.example' 'CHANGE_ME_' data || true
grep -RIn --exclude='*.example' 'example\.com' data || true
```

Both should be empty in active runtime files.

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

## HTTPS

Verify the public hosts for AIOStreams, AIOMetadata, MediaFlow, Headscale/Headplane, StreamViX, both Seanime instances and CometNet.

## Streaming behavior

The installation is not considered reproduced until the AIOStreams final tests in `docs/AIOSTREAMS.md` pass for a movie, normal series episode and anime episode, including TorBox/debrid, Usenet, MediaFlow, Comet, StremThru and all four variants.

---

# 13. 29-service completion checklist

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

# 14. Personalization map — exact file and line

Line numbers below refer to the tracked templates. `bootstrap.sh` copies the same contents to the runtime filename, so the corresponding runtime line is the one to edit.

| File | Line | Value |
|---|---:|---|
| `data/aiometadata/.env.example` | 9-10 | AIOMetadata admin key + addon password |
| `data/aiometadata/.env.example` | 12-13 | TMDB + TVDB keys |
| `data/aiometadata/.env.example` | 16-17 | MDBList + Gemini keys, or blank if disabled |
| `data/aiometadata/.env.example` | 19-20 | AniList OAuth ID/secret, or blank if disabled |
| `data/aiometadata/.env.example` | 21 | public AniList callback hostname |
| `data/aiometadata/.env.example` | 23-25 | Trakt ID/secret/callback, or blank if disabled |
| `data/aiometadata/.env.example` | 32 | fresh AIOMetadata config UUID used for warming |
| `data/aiostreams/.env.example` | 1-2 | public URL + fresh 64-hex `SECRET_KEY` |
| `data/aiostreams/.env.example` | 9-12 | AIO user/password, admin permission + config access key |
| `data/aiostreams/.env.example` | 21 | fresh Jackett API key |
| `data/aiostreams/.env.example` | 26-28 | TMDB access token/API key + TVDB key |
| `data/aiostreams/.env.example` | 31 | trusted UUID for this installation |
| `data/aiostreams/.env.example` | 47 | Comet public token |
| `data/aiostreams/.env.example` | 50 | TorBox key + the same AIO operator credentials |
| `data/cloudflare-ddns/.env.example` | 1-2 | Cloudflare token + wildcard domain |
| `data/comet/.env.example` | 11,13,15 | Comet admin/config passwords + public token |
| `data/comet/.env.example` | 19 | shared PostgreSQL password |
| `data/comet/.env.example` | 57 | Jackett API key |
| `data/comet/.env.example` | 91,94 | replace unused example addon URLs if enabling those scrapers |
| `data/comet/.env.example` | 103 | Comet stream-proxy password |
| `data/comet/.env.example` | 106 | TorBox key |
| `data/comet/.env.example` | 112 | CometNet API key; use the shared Comet token relationship above |
| `data/cometnet/.env.example` | 1 | CometNet API key |
| `data/cometnet/.env.example` | 3-4 | public CometNet WSS hostname + node alias |
| `data/cometnet/.env.example` | 9 | shared PostgreSQL password |
| `data/gluetun/.env.example` | 3-4 | your Mullvad/WireGuard private key + tunnel CIDR |
| `data/headplane/data/config.yaml.example` | 4-5 | public Headscale URL + new 32-char cookie secret |
| `data/headplane/data/config.yaml.example` | 17-18 | public Headscale URL + freshly generated Headscale API key |
| `data/headplane/data/config.yaml.example` | 41-42 | Google OAuth ID/secret if ever enabling Headplane OIDC; reference leaves OIDC disabled |
| `data/headscale/data/config/config.yaml.example` | 1 | public Headscale URL |
| `data/headscale/data/config/config.yaml.example` | 74-76 | extra DNS record hostname + Docker host LAN IP |
| `data/mediaflow-proxy-light/.env.example` | 4 | MediaFlow password |
| `data/oauth2-proxy/.env.example` | 2-4 | Google OAuth ID/secret + callback URL |
| `data/oauth2-proxy/.env.example` | 9 | new OAuth2 Proxy cookie secret |
| `data/oauth2-proxy/.env.example` | 21 | public Headscale whitelist hostname |
| `data/oauth2-proxy/allowed-emails.txt.example` | 1 | allowed Google email |
| `data/pgbouncer/.env.example` | 2 | shared PostgreSQL password |
| `data/pgbouncer/data/userlist.txt.example` | 1 | same PostgreSQL password |
| `data/postgres/.env.example` | 2 | same PostgreSQL password |
| `data/seanime/data/main/config/config.toml.example` | 27 | main Seanime password |
| `data/seanime/data/shared/config/config.toml.example` | 27 | shared Seanime password |
| `data/streamvix/.env.example` | 2-5 | MediaFlow public URL/password, TMDB key, StreamViX public URL |
| `data/stremthru/.env.example` | 6-8 | StremThru user/password/admin + fresh vault secret |
| `data/stremthru/.env.example` | 10-11 | your GitHub user/token if integration is used |
| `data/stremthru/.env.example` | 13 | shared PostgreSQL password |
| `data/tailscale/.env.example` | 2 | Headscale public URL + your real LAN subnet |
| `data/tailscale/.env.example` | 4 | fresh Headscale pre-auth key |
| `data/honey/data/config/config.json.example` | 16-33 | replace every `CHANGE_ME_*` LAN/Proxmox/AMP address and each `example.com` service URL |

Other shared public hostnames such as `aiostreams.example.com`, `aiometadata.example.com`, `mfp.example.com`, `headscale.example.com`, `streamv.example.com` and `cometnet.example.com` appear in their respective templates and must use the same hostname choices used in NPM.

---

# 15. Reset / backup semantics

Recreating a container is normally safe; deleting its persistent directory/named volume is not. In particular, deleting `pgdata`, `warp-data`, Headscale `data/lib`, AIOStreams `data`, NPM `data` or Seanime data resets that application's state.

Back up private runtime state separately. Never add those backups to this public repository.

# Security check before every public push

```bash
git grep -nE '(ghp_|github_pat_|GOCSPX-|AIza|WIREGUARD_PRIVATE_KEY=[^C]|API_TOKEN=[^C]|PASSWORD=[^C])' || true
git status --ignored
```

Review every match manually. Public Git must contain templates/documentation only, never generated credentials or databases.
