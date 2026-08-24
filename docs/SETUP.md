# One-shot configuration wizard

The repository is designed so installation-specific values are entered **once**.

## Fastest path

```bash
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack
chmod +x setup.sh
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
10. runs `docker compose config --quiet` when Docker Compose is available.

The resolved values are stored in `setup.env`, which is gitignored and set to mode `0600`.

## Edit one file instead of answering questions

You can also fill one local file first:

```bash
cp setup.env.example setup.env
chmod 600 setup.env
nano setup.env
./setup.sh --non-interactive
```

Fields left blank in the **auto-generated** section are created automatically.

Optional third-party integrations such as MDBList, Gemini, AniList, Trakt and the StremThru GitHub integration may remain blank when deliberately unused.

## Values the wizard keeps synchronized

The renderer uses one setting for every shared credential, so it is not possible to accidentally use different copies of the same password in different services. This includes:

- PostgreSQL password across PostgreSQL, PgBouncer, Comet, CometNet and StremThru;
- AIOStreams operator user/password across AIO auth and forced native-service credentials;
- Comet public/API token across Comet, CometNet and AIOStreams;
- Jackett API key across Jackett consumers;
- MediaFlow password across MediaFlow and StreamViX;
- TorBox API key across AIOStreams and Comet;
- Google OAuth client across OAuth2 Proxy/Headplane-related templates;
- Headscale hostname across Headscale, Headplane, OAuth2 Proxy and Tailscale;
- server LAN IP/subnet across Tailscale, Headscale and Honey;
- public service hostnames derived from one `BASE_DOMAIN`.

## Runtime-generated keys

On a fresh machine, a Jackett API key and Headscale API/pre-auth keys do not exist before those applications start.

With:

```text
AUTO_RUNTIME_KEYS=true
```

the wizard attempts to start only:

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

## Rerunning

`setup.sh` renders from the tracked `*.example` templates every time, using the current `setup.env`. This means changing a domain, password or LAN address is done in one place and then propagated consistently.

Because application databases and runtime state are separate from the generated config files, rerunning the wizard does not copy or publish databases. Still, review local application-specific changes before intentionally replacing generated configuration on an established installation.

## AIOStreams

AIOStreams runtime configuration lives in its database. The wizard configures its bootstrap `.env` and all credentials shared with the rest of the stack.

For the runtime configuration, import a **sanitized AIOStreams JSON export without credentials** after AIOStreams is running. This is preferable to baking user/indexer/debrid credentials into the public repository.

## What is still a first-run UI task

The wizard removes file-by-file editing, but these pieces are application state and remain deliberate first-run actions:

- create Nginx Proxy Manager admin/certificates/proxy hosts using `docs/NPM.md`;
- complete the AdGuard Home first-run wizard;
- add your own Jackett indexers;
- import your sanitized AIOStreams JSON configuration and add private provider/indexer credentials;
- create/configure any application-specific user state that is stored in a database rather than a text template.

After those steps:

```bash
docker compose --profile all up -d
docker compose --profile all ps
```

Use the end-to-end checks in the main `README.md` before considering the deployment reproduced.
