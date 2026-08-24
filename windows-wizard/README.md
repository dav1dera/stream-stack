# Stream Stack Setup Wizard for Windows

Graphical Windows front-end for the `stream-stack` installer.

The Ubuntu server remains completely headless/CLI. The wizard runs on a Windows PC, connects to the server over SSH, uploads the private `setup.env` directly through SFTP and executes the normal Linux `setup.sh` remotely.

The same executable also includes an **offline Demo / Dry Run mode** for testing the complete input flow without a real domain, API accounts, VPN credentials or an SSH server.

## What it does

The GUI follows the same setup model as the terminal wizard but presents it as a multi-step dark interface:

1. SSH server connection;
2. LAN/network values;
3. public domain names, with standard names or per-service overrides;
4. Mullvad/WireGuard credentials;
5. Cloudflare, TMDB, TVDB and TorBox credentials;
6. Google OAuth2, NPM and application logins;
7. optional integrations;
8. review/validation;
9. remote installation with live logs, or local Dry Run validation;
10. final links/generated credentials, or the generated demo `setup.env` preview.

It keeps the reference stack logic intact. Public FQDNs are operator-defined; internal routing remains the same, including services reached through the Gluetun network namespace and the Headscale -> OAuth2 Proxy -> Headplane routing.

## Demo / Dry Run

On the first page choose **Attiva Demo / Dry Run**.

The wizard automatically fills every required field with values that are deliberately non-production:

- `example.test` for the base domain and all public hostnames;
- `192.0.2.0/24` TEST-NET addresses for server/LAN examples;
- a syntactically valid but unusable WireGuard placeholder key;
- fake Cloudflare, TMDB, TVDB, TorBox, Google OAuth, GitHub and application credentials;
- fake application usernames/passwords and UUIDs.

Dry Run then executes the same Windows-side `setup.env` renderer used by the real wizard and checks that:

- the generated file parses back as `KEY=VALUE` data;
- all required fields are present;
- service hostnames remain under `*.example.test`;
- no `CHANGE_ME_*` placeholder survives in the generated configuration.

In Demo / Dry Run mode the wizard **does not**:

- open an SSH connection;
- contact Cloudflare, TorBox, TMDB, Google or any other external API;
- run Docker or Nginx Proxy Manager;
- execute the remote Linux `setup.sh`.

The completion page shows the generated demo `setup.env`. You can copy it or save it locally as `stream-stack-demo-setup.env` for inspection.

This mode validates the Windows wizard and its generated input configuration. It intentionally does not claim that fake provider credentials can pass real external authentication or that the Linux deployment itself has been exercised.

## Security model

### Real deployment

- SSH passwords, API keys and tokens are kept in process memory on Windows.
- The generated real `setup.env` is not written to the Windows filesystem.
- It is uploaded directly to the Ubuntu server over SFTP.
- The remote file is set to mode `0600`.
- `setup.env` is gitignored by the repository.
- The review page intentionally does not display secret values.
- After setup, only the generated/user-facing credentials needed by the final page are read back over the existing SSH connection and held in memory.
- Closing the application discards those Windows-side values; the authoritative copy remains the private remote `setup.env`.

### Demo / Dry Run

The demo file contains only fake values. It may be explicitly saved to Windows from the completion page so the generated configuration can be inspected.

The SSH client loads existing Windows/OpenSSH known hosts when available. For an unknown server it accepts the key on first connection and shows the SHA-256 fingerprint after the test connection; verify that fingerprint when connecting over an untrusted network.

## Easiest launch from source

Requirements: Windows 10/11 and Python 3.11+.

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
```

Then either double-click:

```text
Start-Wizard.cmd
```

or run:

```powershell
.\run.ps1
```

`run.ps1` creates a local Python virtual environment, installs only the GUI/SSH dependencies and launches `demo_launcher.py`. That entry point extends the hardened `launcher.py` with the offline Demo / Dry Run mode; real deployments still use the same hardened SSH transport and deployment logic.

If PowerShell blocks local scripts, `Start-Wizard.cmd` already invokes it with a process-local execution-policy bypass. You can also use:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

## Standalone EXE

The repository contains a PyInstaller build script:

```powershell
cd windows-wizard
.\build.ps1
```

Output:

```text
windows-wizard\dist\StreamStackSetupWizard.exe
```

GitHub Actions syntax-checks `app.py`, `remote.py`, `launcher.py` and `demo_launcher.py`, then builds the standalone EXE from `demo_launcher.py` as the artifact `StreamStackSetupWizard-Windows`.

## SSH authentication

The real deployment mode supports:

- username + SSH password;
- OpenSSH private key;
- encrypted private key + passphrase;
- SSH agent/default keys when no password/key path is supplied.

The optional sudo password is only used when `Install prerequisites automatically` is enabled. If blank, the wizard falls back to the SSH password. With key authentication and passwordless sudo it uses `sudo -n`.

If Docker is installed during the run, the wizard reconnects SSH after adding the user to the `docker` group so the new group membership applies before continuing.

In Demo / Dry Run mode the **Simula test SSH** button performs no network operation.

## Remote deployment

Default remote path:

```text
~/stream-stack
```

During a real installation the GUI:

- checks Git, Python, Docker and Docker Compose;
- verifies that the SSH user can actually access the Docker daemon;
- optionally installs missing prerequisites on Ubuntu;
- clones the repo, or performs `git pull --ff-only` when it already exists;
- uploads the complete `setup.env` directly via SFTP;
- runs `./setup.sh --non-interactive`;
- therefore uses the same Headscale/Jackett runtime-key automation and NPM desired-state automation as the CLI installer;
- reads back the newly generated user-facing credentials into memory for the completion screen;
- optionally runs `docker compose --profile all up -d`;
- displays `docker compose --profile all ps` in the log when finished.

The GUI does not reimplement the real stack deployment logic. The Linux scripts remain the single source of truth; Windows only collects inputs and orchestrates them remotely.

## Generated credentials on the final page

When passwords/keys are intentionally left blank in a real deployment, Linux generates them. The completion page exposes masked, copyable values for items such as:

- NPM admin;
- AIOStreams user/password/config key;
- StremThru login;
- both Seanime passwords;
- MediaFlow password;
- Comet credentials/API token;
- shared PostgreSQL password;
- Headscale API key;
- Jackett API key.

Use the eye button to reveal one value or `Copia tutte le credenziali generate` to put the generated set on the Windows clipboard.

## Domain behavior

By default, entering:

```text
example.com
```

derives:

```text
aiostreams.example.com
aiometadata.example.com
mfp.example.com
headscale.example.com
streamv.example.com
seanime.example.com
shared-seanime.example.com
cometnet.example.com
stremthru.example.com
portainer.example.com
```

Disable `Usa nomi standard derivati dal dominio base` to type any full hostname for each service. Those hostnames are written to `setup.env` and are therefore consumed by the same Linux renderer, OAuth configuration and NPM automation.

Demo / Dry Run always starts from `example.test`, which is reserved for testing/documentation rather than real public deployment.

## Still manual by design

Application database/account state is not fabricated by the Windows wizard. After a real deployment the remaining expected steps are:

- AdGuard Home first-run wizard;
- add the operator's own Jackett indexers/accounts;
- import the sanitized AIOStreams JSON and enter provider/indexer/Usenet credentials;
- verify streaming behavior and AIOStreams variants.

The final real-deployment page provides shortcuts for the main local/public UIs.
