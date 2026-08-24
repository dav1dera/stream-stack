# Stream Stack

<p align="center">
  <strong>Stack Docker self-hosted riproducibile per streaming, metadata, proxy, DNS, VPN e gestione remota.</strong>
</p>

<p align="center">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
  <img alt="Ubuntu" src="https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white">
  <img alt="Windows Wizard" src="https://img.shields.io/badge/Windows-Setup%20Wizard-6C5CE7?logo=windows11&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/Config-sanitizzata-22C55E">
</p>

> [!IMPORTANT]
> Questa repository non serve soltanto ad avviare dei container. L'obiettivo è permettere a una nuova installazione di ricostruire **la stessa architettura e la stessa logica operativa dello stack di riferimento**, usando però domini, account, API key e credenziali appartenenti a chi installa.

---

## Indice

- [Panoramica](#panoramica)
- [Wizard grafico per Windows](#wizard-grafico-per-windows)
- [Architettura](#architettura)
- [Installazione rapida](#installazione-rapida)
- [Cosa chiede il setup](#cosa-chiede-il-setup)
- [Domini e Nginx Proxy Manager](#domini-e-nginx-proxy-manager)
- [AIOStreams](#aiostreams)
- [Operazioni ancora manuali](#operazioni-ancora-manuali)
- [Verifica finale](#verifica-finale)
- [Sicurezza](#sicurezza)

---

# Panoramica

La repo conserva la topologia del deployment originale ma **non pubblica stato runtime o dati sensibili**.

### Servizi inclusi

| Area | Servizi principali |
|---|---|
| Streaming | AIOStreams, Comet, CometNet, StremThru, StreamViX, MediaFlow Proxy Light |
| Anime | Seanime principale + Seanime condiviso |
| Metadata | AIOMetadata |
| Indexing | Jackett |
| Database | PostgreSQL, PgBouncer, Redis |
| VPN / Proxy | Gluetun, MicroWARP, GOST |
| DNS | AdGuard Home, DNSCrypt Proxy, Cloudflare DDNS |
| Accesso remoto | Headscale, Tailscale, Headplane, OAuth2 Proxy |
| Reverse proxy | Nginx Proxy Manager |
| Gestione | Portainer, Honey, Watchtower, Deunhealth |
| Extra | TeamSpeak |

In totale lo stack mantiene la struttura a **29 servizi** del deployment di riferimento.

### Cosa non viene pubblicato

- database applicativi;
- password, API key e token;
- certificati Let's Encrypt;
- identità Headscale / Tailscale / WARP;
- configurazioni private degli indexer;
- librerie e stato Seanime;
- database AIOStreams;
- cache e file runtime;
- credenziali Usenet o provider.

Questi elementi vengono rigenerati o reinseriti durante il setup.

---

# Wizard grafico per Windows

Per chi non vuole lavorare file per file sul server è disponibile un **wizard grafico Windows**.

Il server Ubuntu può restare completamente **headless / CLI**: la GUI gira sul PC Windows e si collega via **SSH/SFTP**.

<p align="center">
  <img src="assets/screenshots/wizard-home.svg" alt="Schermata iniziale Stream Stack Setup Wizard" width="100%">
</p>

Il wizard guida attraverso:

1. connessione SSH al server;
2. rete locale e subnet;
3. dominio base e hostname pubblici;
4. WireGuard / Gluetun;
5. Cloudflare, TMDB, TVDB e TorBox;
6. OAuth2, NPM e login applicativi;
7. integrazioni opzionali;
8. riepilogo e validazione;
9. installazione remota con log in tempo reale;
10. stato finale e credenziali generate.

## Rete e domini

Gli hostname non sono hardcoded. È possibile usare i nomi standard derivati dal dominio base oppure scegliere un FQDN diverso per ogni servizio.

<p align="center">
  <img src="assets/screenshots/wizard-network.svg" alt="Configurazione rete e domini del wizard" width="100%">
</p>

Esempio con nomi standard:

```text
aiostreams.example.com
aiometadata.example.com
mfp.example.com
headscale.example.com
seanime.example.com
shared-seanime.example.com
cometnet.example.com
stremthru.example.com
streamv.example.com
portainer.example.com
```

Ma è perfettamente valido usare, per esempio:

```text
streams.miodominio.it
anime.casa.net
vpn.altrodominio.org
proxy.example.com
```

La logica interna dello stack resta invariata.

## Schermata finale

Al termine il wizard mostra log, stato dei servizi e le credenziali generate automaticamente.

<p align="center">
  <img src="assets/screenshots/wizard-complete.svg" alt="Installazione Stream Stack completata" width="100%">
</p>

> [!NOTE]
> Le immagini sopra sono anteprime dell'interfaccia del wizard; la GUI effettiva è implementata in `windows-wizard/`.

## Avvio del wizard su Windows

Dopo aver clonato la repo:

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
```

Il metodo più semplice è fare doppio click su:

```text
Start-Wizard.cmd
```

oppure da PowerShell:

```powershell
.\run.ps1
```

È presente anche uno script PyInstaller per generare un eseguibile standalone:

```powershell
.\build.ps1
```

Output previsto:

```text
windows-wizard\dist\StreamStackSetupWizard.exe
```

---

# Architettura

Schema logico semplificato:

```text
                        Internet
                           │
                    Cloudflare DNS
                           │
                     TCP 80 / 443
                           │
                Nginx Proxy Manager
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   AIOStreams          Headscale           Seanime
        │                  │                  │
        │             /admin → OAuth2         │
        │                  │                  │
        │              Headplane              │
        │                                     │
        ├────────── MediaFlow / Comet ─────────┤
        │
        └──── servizi attraverso Gluetun ──────┐
                                              │
                                    Mullvad / WireGuard
                                              │
                                       WARP / GOST
```

DNS locale:

```text
Client LAN
   │
AdGuard Home :53
   │
DNSCrypt Proxy :5353
   │
resolver upstream
```

Database:

```text
PostgreSQL
   │
PgBouncer :6432
   ├── Comet
   ├── CometNet
   └── StremThru

Redis
   ├── AIOStreams / servizi collegati
   └── AIOMetadata / cache
```

---

# Installazione rapida

## Metodo 1 — Wizard Windows

È il metodo consigliato se il server è headless.

```text
Windows GUI → SSH → Ubuntu Server → setup.sh → Docker Compose
```

Il wizard:

- verifica SSH e prerequisiti;
- clona o aggiorna la repo sul server;
- scrive `setup.env` direttamente via SFTP;
- imposta il file a `0600`;
- esegue il setup Linux;
- configura Nginx Proxy Manager;
- genera le chiavi runtime dove possibile;
- avvia lo stack;
- mostra i log;
- recupera le credenziali generate per mostrarle nella schermata finale.

## Metodo 2 — Server CLI

Su Ubuntu:

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
./setup.sh
```

Oppure compilando un solo file:

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
```

Non è più necessario modificare manualmente decine di `.env` o file di configurazione.

---

# Preparazione del server

Target di riferimento:

```text
Ubuntu Server 24.04 LTS
Docker Engine
Docker Compose v2
```

Servono inoltre:

- IP LAN statico o riservato via DHCP;
- accesso a `/dev/net/tun`;
- TCP 80 e 443 inoltrate verso il server;
- TCP/UDP 53 disponibile per AdGuard Home;
- subnet Docker `172.18.0.0/24` e `172.19.0.0/24` non sovrapposte alla LAN;
- dominio pubblico gestibile via DNS.

Per Headscale / subnet routing:

```bash
cat <<'EOF' | sudo tee /etc/sysctl.d/99-stream-stack.conf
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF
sudo sysctl --system
```

Se la porta 53 è occupata da `systemd-resolved`, liberarla prima di avviare AdGuard.

---

# Cosa chiede il setup

Il setup usa **un'unica sorgente di verità**: `setup.env`.

### Valori tipicamente inseriti dall'utente

| Categoria | Valori |
|---|---|
| Rete | IP server, subnet LAN, timezone |
| Domini | dominio base + eventuali hostname personalizzati |
| Cloudflare | API token |
| VPN | WireGuard private key + address CIDR |
| Metadata | TMDB API key, TMDB read token, TVDB API key |
| Debrid | TorBox API key |
| OAuth | Google Client ID, Client Secret, email consentita |

### Valori generati automaticamente se lasciati vuoti

- password PostgreSQL;
- AIOStreams `SECRET_KEY`;
- password operatore AIOStreams;
- AIO config access key;
- password AIOMetadata;
- password Comet;
- token Comet / CometNet;
- password MediaFlow;
- secret Headplane;
- cookie secret OAuth2 Proxy;
- password e vault secret StremThru;
- password Seanime principale;
- password Seanime condiviso;
- password admin NPM su installazione nuova.

I valori condivisi vengono propagati automaticamente in tutti i servizi che devono usare la stessa credenziale.

---

# Domini e Nginx Proxy Manager

NPM viene gestito come **desired state** dal setup.

Se il proxy host esiste viene aggiornato; se non esiste viene creato.

| Servizio pubblico | Target interno | Porta | WebSocket |
|---|---|---:|:---:|
| AIOStreams | `aiostreams` | 4444 | No |
| AIOMetadata | `aiometadata` | 1337 | Sì |
| MediaFlow | `mediaflow-proxy-light` | 8888 | No |
| Headscale | `headscale` | 8080 | Sì |
| Portainer | `portainer` | 9000 | No |
| StremThru | `gluetun` | 9090 | No |
| Seanime | `gluetun` | 43211 | Sì |
| Seanime Shared | `gluetun` | 43311 | Sì |
| CometNet | `gluetun` | 8765 | Sì |
| StreamViX | `gluetun` | 7860 | No |

Per i proxy gestiti vengono mantenuti:

- HTTPS;
- Force SSL;
- HTTP/2;
- HSTS;
- Block Common Exploits;
- WebSocket soltanto dove necessario.

## Headscale + Headplane

Il dominio Headscale usa una configurazione particolare:

```text
/                 → Headscale
/admin            → OAuth2 Proxy → Headplane
/oauth2/*          → OAuth2 Proxy
/oauth2/callback   → OAuth2 Proxy
```

Questa logica viene preservata anche se l'utente sceglie un hostname completamente diverso.

Documentazione tecnica aggiuntiva: [`docs/NPM.md`](docs/NPM.md).

---

# AIOStreams

La configurazione runtime di AIOStreams vive nel database dell'applicazione e non viene pubblicata.

Il metodo consigliato è:

1. avviare AIOStreams con il setup della repo;
2. importare un **JSON sanitizzato** della configurazione;
3. inserire le proprie credenziali provider / indexer / Usenet;
4. verificare le varianti e i filtri.

In questo modo la logica può essere replicata senza pubblicare database o token.

La guida di riferimento è disponibile in [`docs/AIOSTREAMS.md`](docs/AIOSTREAMS.md).

---

# Runtime keys automatiche

Su un'installazione nuova alcune chiavi non esistono prima del primo avvio.

Con:

```text
AUTO_RUNTIME_KEYS=true
```

il setup prova automaticamente a:

- rilevare l'API key generata da Jackett;
- creare l'utente Headscale;
- generare la Headscale API key per Headplane;
- generare una pre-auth key per il container Tailscale;
- riscrivere i file dipendenti con i nuovi valori.

---

# Operazioni ancora manuali

Per scelta, alcune informazioni non vengono inventate o pubblicate.

### AdGuard Home

Primo avvio:

```text
http://SERVER_LAN_IP:3010
```

Impostazioni previste:

```text
Web UI:     0.0.0.0:90
DNS:        0.0.0.0:53
Upstream:   172.18.0.4:5353
```

### Jackett

Aprire:

```text
http://SERVER_LAN_IP:9117
```

e aggiungere i propri indexer.

### AIOStreams

Importare il JSON sanitizzato e aggiungere le credenziali private.

### Portainer

Creare l'account admin della nuova installazione e selezionare l'ambiente Docker locale.

### Seanime

Database, librerie e stato utente vengono creati localmente e non fanno parte della repo pubblica.

---

# Avvio dello stack

```bash
docker compose --profile all up -d
docker compose --profile all ps
```

Servizi critici come Gluetun devono risultare `healthy` prima di considerare il deployment completato.

---

# Verifica finale

### Placeholder non risolti

```bash
grep -RIn --exclude='*.example' 'CHANGE_ME_' data || true
grep -RIn --exclude='*.example' 'example\.com' data || true
```

Non dovrebbero produrre output nei file runtime attivi.

### Docker Compose

```bash
docker compose config --quiet
docker compose --profile all ps
```

### PostgreSQL

```bash
docker exec postgres psql -U postgres -Atc \
  "SELECT datname FROM pg_database WHERE datname IN ('comet','stremthru') ORDER BY datname;"
```

### VPN

```bash
docker inspect --format '{{.State.Health.Status}}' gluetun
docker exec gluetun wget -qO- https://ipinfo.io/ip || true
```

### DNS

```bash
dig @SERVER_LAN_IP cloudflare.com
dig @SERVER_LAN_IP github.com
```

### Headscale

```bash
docker exec -it headscale headscale users list
docker exec -it headscale headscale nodes list
```

### Streaming

Il deployment non è considerato realmente riprodotto finché AIOStreams non viene verificato con:

- film;
- episodio serie;
- episodio anime;
- TorBox / debrid;
- Usenet;
- MediaFlow;
- Comet;
- StremThru;
- tutte le varianti/profili previsti.

---

# Checklist servizi

<details>
<summary><strong>Mostra i 29 servizi</strong></summary>

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

</details>

---

# Sicurezza

`setup.env` contiene segreti ed è escluso da Git.

Il wizard Windows:

- mantiene i secret in memoria sul PC;
- invia `setup.env` direttamente via SFTP;
- imposta il file remoto a `0600`;
- non committa credenziali;
- non include database o certificati nella repo pubblica.

Prima di ogni push pubblico è comunque consigliato controllare:

```bash
git grep -nE '(ghp_|github_pat_|GOCSPX-|AIza|WIREGUARD_PRIVATE_KEY=[^C]|API_TOKEN=[^C]|PASSWORD=[^C])' || true
git status --ignored
```

---

<p align="center">
  <strong>Un solo setup, una sola sorgente di configurazione, stessa logica dello stack di riferimento.</strong>
</p>
