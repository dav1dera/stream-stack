# One-shot configuration wizard

The repository is designed so installation-specific values are entered **once**.

## Fastest path

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
./setup.sh
```

On the first run, `setup.sh`:

1. creates a local `setup.env` from `setup.env.example`;
2. asks only for missing required installation values;
3. generates strong local-only passwords/tokens/secrets where possible;
4. runs the normal template bootstrap;
5. renders every tracked `*.example` file into the real untracked runtime file;
6. replaces shared values consistently everywhere they are used;
7. optionally starts only Gluetun, Headscale and Jackett to obtain runtime-generated Headscale/Jackett keys;
8. writes those discovered values back into the generated runtime configuration;
9. verifies that active files contain no `CHANGE_ME_*`, `example.com`, or example-LAN placeholders;
10. validates the Compose model;
11. starts Cloudflare DDNS + Nginx Proxy Manager;
12. creates/reuses the NPM admin and shared Let's Encrypt certificate;
13. creates or updates the full reference reverse-proxy topology through the NPM API.

The resolved values are stored in `setup.env`, which is gitignored and set to mode `0600`.

## Edit one file instead of answering questions

You can also fill one local file first:

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
```

Fields left blank in the **auto-generated** sections are created automatically.

Optional third-party integrations such as MDBList, Gemini, AniList, Trakt and the StremThru GitHub integration may remain blank when deliberately unused.

## Domains: defaults or completely custom names

`BASE_DOMAIN` is only the default naming source.

For example:

```text
BASE_DOMAIN=mydomain.net
```

produces the normal defaults:

```text
aiostreams.mydomain.net
mfp.mydomain.net
headscale.mydomain.net
seanime.mydomain.net
...
```

But every public service has an optional full-FQDN override in `setup.env`:

```text
AIOSTREAMS_HOST=aio.example.org
AIOMETADATA_HOST=metadata.example.org
MEDIAFLOW_HOST=streamproxy.example.net
HEADSCALE_HOST=mesh.example.com
STREAMVIX_HOST=vix.example.com
SEANIME_HOST=anime.example.net
SEANIME_SHARED_HOST=anime-shared.example.net
COMETNET_HOST=cometnet.example.org
STREMTHRU_HOST=stremthru.example.org
PORTAINER_HOST=docker.example.com
```

The labels do **not** have to match the reference names. They may even belong to different Cloudflare zones if the API token has permission for them.

The wizard propagates those choices everywhere they matter: application URLs, OAuth callback/whitelist values, Headscale/Headplane config, Honey, Cloudflare DDNS, NPM certificates and NPM proxy hosts.

## Values the wizard keeps synchronized

The renderer uses one setting for every shared credential, so it is not possible to accidentally use different copies of the same password in different services. This includes:

- PostgreSQL password across PostgreSQL, PgBouncer, Comet, CometNet and StremThru;
- AIOStreams operator user/password across AIO auth and forced native-service credentials;
- Comet public/API token across Comet, CometNet and AIOStreams;
- Jackett API key across Jackett consumers;
- MediaFlow password across MediaFlow and StreamViX;
- TorBox API key across AIOStreams and Comet;
- Google OAuth client across OAuth2 Proxy/Headplane-related templates;
- Headscale hostname across Headscale, Headplane, OAuth2 Proxy, Tailscale and NPM;
- server LAN IP/subnet across Tailscale, Headscale and Honey;
- selected public hostnames across service configs, DDNS and reverse proxying.

## Runtime-generated keys

On a fresh machine, a Jackett API key and Headscale API/pre-auth keys do not exist before those applications start.

With:

```text
AUTO_RUNTIME_KEYS=true
```

the core wizard attempts to start only:

- `gluetun`
- `headscale`
- `jackett`

It then:

- reads the generated Jackett API key from Jackett's `ServerConfig.json`;
- creates the configured Headscale user if necessary;
- creates a Headscale API key for Headplane;
- creates a Headscale pre-auth key for the Tailscale container;
- re-renders all runtime files with those values.

If Docker is unavailable or one of these automatic steps fails, the wizard exits with the unresolved value listed. Put the value in `setup.env` and run `./setup.sh` again.

To disable runtime bootstrap deliberately:

```bash
./setup.sh --no-runtime-keys
```

In that mode, provide `JACKETT_API_KEY`, `HEADSCALE_API_KEY` and `HEADSCALE_AUTHKEY` yourself.

## Nginx Proxy Manager automation

NPM is no longer a required manual first-run step.

The relevant settings are:

```text
NPM_ADMIN_EMAIL=
NPM_ADMIN_PASSWORD=
LETSENCRYPT_EMAIL=
AUTO_CONFIGURE_NPM=true
```

On a fresh NPM database:

- the admin email defaults to `ALLOWED_EMAIL` when blank;
- the admin password is generated locally when blank;
- NPM's supported `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` variables are injected before first startup;
- the Let's Encrypt email defaults to `ALLOWED_EMAIL`.

Then `scripts/npm_apply.py`:

1. expands Cloudflare DDNS to include the wildcard base domain and every selected public hostname;
2. starts Cloudflare DDNS and NPM;
3. authenticates to the local NPM API;
4. reuses an existing certificate when it already covers all selected hosts, otherwise requests one shared Let's Encrypt SAN certificate;
5. creates or updates all reference proxy hosts;
6. installs the special Headscale `/admin` + `/oauth2/` routing dynamically with the chosen Headscale hostname;
7. verifies that every required hostname exists.

The fixed routing logic is documented in **[NPM.md](NPM.md)**.

The NPM apply step is idempotent: rerunning it updates matching domains instead of blindly duplicating them, and unrelated/manual NPM hosts are not deleted.

Skip it with:

```bash
./setup.sh --no-npm
```

or:

```text
AUTO_CONFIGURE_NPM=false
```

## Rerunning

`setup.sh` renders from the tracked `*.example` templates every time, using the current `setup.env`. This means changing a domain, password or LAN address is done in one place and then propagated consistently.

NPM is also reconciled again on rerun. Existing hosts using the selected domain names are updated in place. Other NPM hosts are left untouched.

Because application databases and runtime state are separate from the generated config files, rerunning the wizard does not copy or publish databases. Still, review local application-specific changes before intentionally replacing generated configuration on an established installation.

## AIOStreams

AIOStreams runtime configuration lives in its database. The wizard configures its bootstrap `.env` and all credentials shared with the rest of the stack.

For the runtime configuration, import a **sanitized AIOStreams JSON export without credentials** after AIOStreams is running. This is preferable to baking user/indexer/debrid/Usenet credentials into the public repository.

## What still remains a first-run application task

After the one-shot wizard, the remaining tasks are application state that should not be baked into a public repo:

- complete the AdGuard Home first-run wizard;
- add your own Jackett indexers/login state;
- import your sanitized AIOStreams JSON configuration and add private provider/indexer/Usenet credentials;
- create/configure any other application-specific user state stored only in a database.

Nginx Proxy Manager host creation, SSL assignment and the Headscale/Headplane OAuth routing are **not** on this manual list anymore.

After those application-state steps:

```bash
docker compose --profile all up -d
docker compose --profile all ps
```

Use the end-to-end checks in the main `README.md` before considering the deployment reproduced.
