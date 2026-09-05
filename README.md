# Stream Stack

<p align="center">
  <strong>Stack Docker self-hosted riproducibile per streaming, metadata, proxy, VPN, database e accesso remoto.</strong>
</p>

<p align="center">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
  <img alt="Ubuntu" src="https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white">
  <img alt="Windows Wizard" src="https://img.shields.io/badge/Windows-Setup%20Wizard-6C5CE7?logo=windows11&logoColor=white">
  <img alt="Servizi" src="https://img.shields.io/badge/Servizi-31-22C55E">
  <img alt="Config" src="https://img.shields.io/badge/Config-sanitizzata-0EA5E9">
</p>

> [!IMPORTANT]
> La modalità consigliata è il **Windows Setup Wizard con Strict Acceptance attivo**. In questa modalità la schermata **Completato** viene mostrata solo dopo che container, porte LAN, DNS, TLS, reverse proxy e routing pubblico previsto hanno superato i test automatici.

---

## Obiettivo

`stream-stack` è il quick setup / disaster recovery pubblico della topologia privata `streams-aio`.

La repository non copia database, token, certificati o stato personale. Ricrea invece automaticamente:

- topologia Docker;
- file `.env` e configurazioni generate;
- password e secret locali;
- PostgreSQL / PgBouncer / Redis;
- Gluetun, MicroWARP e GOST;
- Nginx Proxy Manager;
- Cloudflare DDNS;
- certificati HTTPS;
- proxy host pubblici e LAN-only;
- Headscale / Tailscale / Headplane / OAuth2 Proxy;
- chiavi runtime Headscale e Jackett quando possibile;
- tuning corrente di Comet/PostgreSQL/PgBouncer;
- test finali di readiness.

Il risultato è pensato per essere il più vicino possibile a:

```text
prepara router + credenziali
        ↓
StreamStackSetupWizard.exe
        ↓
Installa
        ↓
attesa automatica DNS / SSL / container
        ↓
ACCEPTANCE OK
        ↓
Completato
```

---

# Prima di avviare il wizard

Per un fresh install pubblico, prepara questi punti **prima di premere Installa**.

## 1. Server

- Ubuntu Server 24.04 consigliato;
- IP LAN stabile/statico;
- accesso SSH funzionante;
- almeno Python 3; Git/Docker possono essere installati dal wizard se abiliti l'opzione dedicata.

## 2. Router

Inoltra verso `SERVER_LAN_IP`:

```text
TCP 80  → SERVER_LAN_IP:80
TCP 443 → SERVER_LAN_IP:443
```

Non servono regole UDP per Nginx Proxy Manager / HTTPS.

La porta **80 deve essere raggiungibile già durante il wizard**, perché Let's Encrypt usa HTTP-01 per il certificato. La 443 viene poi usata per HTTPS.

> [!WARNING]
> Se la linea è dietro CGNAT e non puoi ricevere connessioni TCP 80/443 dall'esterno, la modalità HTTPS automatica con HTTP-01 non può essere considerata one-click finché non risolvi l'accesso pubblico.

## 3. Dominio / Cloudflare

Servono:

- dominio gestito su Cloudflare;
- API token con permessi DNS edit sulle zone usate;
- porte 80/443 inoltrate al server.

Cloudflare DDNS viene configurato automaticamente. Lo stack attende che i record risultino visibili sul resolver pubblico Cloudflare prima di chiedere il certificato.

## 4. Credenziali richieste

Il wizard richiede i valori realmente necessari, tra cui:

- Cloudflare API token;
- WireGuard/Mullvad;
- TMDB;
- TVDB;
- TorBox;
- Google OAuth2.

Le integrazioni opzionali possono restare vuote.

---

# Windows Setup Wizard

## Avvio da sorgente

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

Oppure doppio click su:

```text
Start-Wizard.cmd
```

Per creare l'EXE:

```powershell
.\build.ps1
```

Output:

```text
windows-wizard\dist\StreamStackSetupWizard.exe
```

---

# Opzioni importanti del wizard

Le opzioni raccomandate per un'installazione one-click completa sono:

```text
Genera automaticamente chiavi runtime          ON
Configura automaticamente NPM                  ON
Avvia tutto lo stack al termine                ON
Verifica end-to-end stretta                    ON
Timeout DNS / SSL / servizi                    600 s
TCP 80 e TCP 443 inoltrate sul router          CONFERMATO
```

### `AUTO_RUNTIME_KEYS`

Avvia temporaneamente i servizi necessari per ottenere automaticamente:

- Jackett API key;
- Headscale user;
- Headscale API key;
- Headscale pre-auth key per Tailscale.

### `AUTO_CONFIGURE_NPM`

Configura automaticamente:

- account NPM iniziale;
- Cloudflare DDNS;
- certificato Let's Encrypt condiviso;
- proxy host;
- HTTPS / HTTP2 / HSTS;
- routing speciale Headscale → OAuth2 Proxy → Headplane;
- policy LAN-only per i servizi interni.

### `PUBLIC_READY_TIMEOUT`

Default:

```text
600
```

È il tempo massimo in secondi che il setup può attendere automaticamente per:

- propagazione DNS pubblica;
- readiness dei container;
- healthcheck;
- apertura delle porte applicative;
- HTTPS/TLS;
- reverse proxy.

Valori supportati dal wizard: `30`–`3600` secondi.

### `STRICT_ACCEPTANCE`

Default:

```text
true
```

Con questa opzione attiva il wizard **non arriva a Completato** se i test finali falliscono.

### Conferma router 80/443

Il wizard richiede esplicitamente la conferma che:

```text
TCP 80  → server
TCP 443 → server
```

siano già configurate. Senza conferma, con NPM + Strict Acceptance attivi, l'installazione non parte.

---

# Cosa verifica il test finale

Dopo `docker compose --profile all up -d`, il wizard esegue:

```bash
python3 scripts/acceptance.py
```

Il test riprova automaticamente fino a `PUBLIC_READY_TIMEOUT`.

Per ottenere:

```text
ACCEPTANCE OK
```

devono passare almeno questi controlli:

1. tutti i servizi Compose del profilo `all` devono essere `running`;
2. i container con healthcheck devono essere `healthy`;
3. tutte le porte LAN attese devono essere raggiungibili;
4. gli hostname pubblici non-LAN-only devono risolvere;
5. la connessione TLS deve validare hostname e certificato;
6. NPM deve restituire una risposta HTTP non-5xx;
7. `/admin` di Headscale deve raggiungere il flusso OAuth previsto.

Se uno di questi punti non diventa valido entro il timeout:

```text
ACCEPTANCE FAILED
```

il wizard si ferma e mostra il motivo nel log. Non presenta lo stack come pronto.

## Test manuale CLI

Puoi rilanciarlo quando vuoi:

```bash
cd ~/stream-stack
python3 scripts/acceptance.py --timeout 600
```

---

# Attesa automatica DNS e certificati

Prima di richiedere il certificato, `npm_current.py` controlla tramite DNS-over-HTTPS di Cloudflare che tutti gli hostname siano diventati pubblicamente risolvibili.

Flusso:

```text
Cloudflare DDNS start
        ↓
wait public DNS
        ↓
NPM API ready
        ↓
Let's Encrypt HTTP-01
        ↓
proxy host
        ↓
full stack
        ↓
strict acceptance
```

Se Let's Encrypt fallisce, il setup segnala esplicitamente di controllare:

```text
TCP 80
TCP 443
SERVER_LAN_IP
DNS Cloudflare
```

---

# Topologia attuale

### 31 servizi

| Area | Servizi |
|---|---|
| Streaming / addon | AIOStreams, Comet, CometNet, StremThru, StreamViX, TvVoo |
| Proxy playback | MediaFlow Proxy Light, EasyProxy |
| Config management | AIOManager |
| Metadata | AIOMetadata |
| Anime | Seanime, Seanime Shared |
| Indexing | Jackett |
| Database | PostgreSQL, PgBouncer, Redis |
| VPN / proxy | Gluetun, MicroWARP, GOST |
| DNS | DNSCrypt Proxy, Cloudflare DDNS |
| Accesso remoto | Headscale, Tailscale, Headplane, OAuth2 Proxy |
| Reverse proxy | Nginx Proxy Manager |
| Gestione | Portainer, Honey, Watchtower, Deunhealth |
| Extra | TeamSpeak |

AdGuard Home è intenzionalmente esterno a questo Compose. In questo modo il DNS della LAN non dipende dal ciclo di vita dello stack streaming.

---

# Routing pubblico e LAN-only

Il setup corrente genera automaticamente i seguenti host NPM.

## Pubblici HTTPS

```text
AIOStreams
AIOMetadata
MediaFlow Proxy
EasyProxy
Headscale / Headplane OAuth
Seanime
Seanime Shared
CometNet
```

## HTTPS ma LAN-only

Le richieste vengono limitate automaticamente a `LAN_SUBNET`:

```text
Portainer
StremThru
StreamViX
TvVoo
AIOManager
```

EasyProxy resta pubblico perché viene usato direttamente dai client per il playback HLS.

Comet resta raggiungibile localmente sulla porta `2020` e viene consumato internamente da AIOStreams.

---

# Architettura sintetica

```text
Internet
   │
Cloudflare DNS/DDNS
   │
TCP 80/443
   │
Nginx Proxy Manager
   ├── AIOStreams
   ├── AIOMetadata
   ├── MediaFlow
   ├── EasyProxy
   ├── Headscale / OAuth2 / Headplane
   ├── Seanime / Seanime Shared
   ├── CometNet
   └── host LAN-only
```

Catena streaming:

```text
AIOStreams
   ├── Comet
   ├── StremThru
   ├── Jackett
   ├── StreamViX
   ├── TvVoo
   ├── AIOMetadata
   └── proxy / provider esterni

TvVoo / StreamViX
        ↓
EasyProxy / MediaFlow
        ↓
playback client
```

VPN/proxy:

```text
Gluetun → Mullvad/WireGuard

MicroWARP SOCKS5 :1080
        ↓
GOST HTTP :8082
        ↓
WARP fallback
```

MicroWARP viene eseguito solo nella rete Docker e usa esplicitamente:

```text
ALLOW_NO_AUTH=1
```

Il SOCKS non viene pubblicato direttamente sull'host.

---

# Database

```text
PostgreSQL
   │
PgBouncer :6432
   ├── comet
   ├── stremthru
   └── aiomanager
```

La configurazione pubblica segue il tuning corrente del deployment di riferimento:

```text
PostgreSQL max_connections     120
shared_buffers                 4GB
work_mem globale               8MB
synchronous_commit globale     on
checkpoint_timeout             15min
checkpoint_completion_target   0.95

Comet synchronous_commit       off
Comet work_mem                 16MB
StremThru synchronous_commit   off
```

PgBouncer:

```text
Comet       pool 32 / max DB 40
StremThru   pool 16 / max DB 24
AIOManager  pool  8 / max DB 12
Default     pool 16
Reserve     4
```

Comet background scraper:

```text
workers                         8
max movies/run                700
max series/run                500
max episodes/series/run        25
run time budget              3600s
```

---

# Cosa viene generato automaticamente

Il wizard genera localmente, senza committarli:

- PostgreSQL password;
- AIOStreams secret/password/config key;
- AIOMetadata password/keys;
- Comet admin/config/API token;
- CometNet API token;
- MediaFlow password;
- EasyProxy password;
- AIOManager encryption key;
- StremThru password/vault secret;
- Headplane secret;
- OAuth2 cookie secret;
- Seanime passwords;
- NPM admin password quando necessario.

`setup.env` viene scritto sul server con mode `0600` ed è ignorato da Git.

---

# Cosa resta manuale dopo ACCEPTANCE OK

L'infrastruttura è pronta, ma alcuni **stati applicativi personali** non vengono inventati dal wizard.

### Jackett

Apri:

```text
http://SERVER_LAN_IP:9117
```

e aggiungi gli indexer/account che vuoi usare.

### AIOStreams

Importa il tuo backup/config JSON sanitizzato e aggiungi le credenziali private di provider/indexer/Usenet/debrid che non devono essere pubblicate nella repo.

### Seanime / Portainer

Solo eventuale stato personale specifico dell'applicazione.

Questi passaggi non sono errori di deployment: sono dati privati/operator-specific che la repository non può conoscere in anticipo.

---

# Installazione CLI

Il wizard Windows è il percorso raccomandato, ma il setup Linux resta utilizzabile direttamente.

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
./setup.sh
```

Oppure:

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
docker compose --profile all up -d
python3 scripts/acceptance.py --timeout 600
```

Nota: la conferma grafica delle porte router appartiene al wizard Windows. In CLI devi assicurarti manualmente che TCP 80/443 siano già inoltrate.

---

# Demo / Dry Run

Il Windows Wizard include una modalità Demo / Dry Run che:

- usa `example.test`;
- usa indirizzi TEST-NET;
- genera un `setup.env` fittizio;
- valida il flusso GUI;
- non usa SSH;
- non avvia Docker;
- non contatta Cloudflare o provider esterni;
- non esegue l'acceptance reale.

È utile per testare il wizard senza modificare un server.

---

# Verifica repository

Validazione strutturale:

```bash
python3 scripts/validate_stack.py
```

Bootstrap template + Compose:

```bash
bash scripts/bootstrap.sh
docker compose config --quiet
```

GitHub Actions controlla automaticamente:

- sintassi Python;
- struttura dei 31 servizi;
- template richiesti;
- tuning atteso;
- plumbing Strict Acceptance;
- Docker Compose;
- build del Windows Setup Wizard.

---

# Sicurezza

- nessuna password/token privata della repo sorgente viene copiata;
- `setup.env` è gitignored e `0600`;
- i secret vengono generati localmente;
- i servizi LAN-only sono limitati alla subnet configurata;
- MicroWARP no-auth resta interno alla rete Docker;
- database e stato applicativo privato non vengono pubblicati;
- il validator cerca riferimenti hardcoded noti prima delle build.

> [!WARNING]
> Prima di pubblicare nuovi file provenienti da un deployment privato, verifica sempre che non contengano token, password, email private, certificati, database o stato applicativo sensibile.
