# Stream Stack Setup Wizard for Windows

Graphical Windows front-end for the `stream-stack` installer.

The Ubuntu server remains completely headless/CLI. The wizard runs on a Windows PC, connects to the server over SSH, uploads the private `setup.env` directly through SFTP and executes the normal Linux `setup.sh` remotely.

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
9. remote installation with live logs;
10. final links and remaining first-run tasks.

It keeps the reference stack logic intact. Public FQDNs are operator-defined; internal routing remains the same, including services reached through the Gluetun network namespace and the Headscale -> OAuth2 Proxy -> Headplane routing.

## Security model

- SSH passwords, API keys and tokens are kept in process memory on Windows.
- The generated `setup.env` is not written to the Windows filesystem.
- It is uploaded directly to the Ubuntu server over SFTP.
- The remote file is set to mode `0600`.
- `setup.env` is gitignored by the repository.
- The review page intentionally does not display secret values.

The SSH client loads existing Windows/OpenSSH known hosts when available. For an unknown server it accepts the key on first connection and shows the resulting fingerprint after the test connection; verify that fingerprint when connecting to an untrusted network.

## Run from source

Requirements: Windows 10/11 and Python 3.11+.

From PowerShell:

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

`run.ps1` creates a local Python virtual environment, installs only the GUI/SSH dependencies and launches the wizard.

If PowerShell blocks local scripts for the current process:

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

GitHub Actions also syntax-checks the Python source and builds the same standalone EXE as the artifact `StreamStackSetupWizard-Windows`.

## SSH authentication

The wizard supports:

- username + SSH password;
- OpenSSH private key;
- encrypted private key + passphrase;
- SSH agent/default keys when no password/key path is supplied.

The optional sudo password is only used when `Install prerequisites automatically` is enabled. If blank, the wizard falls back to the SSH password for sudo.

## Remote deployment

Default remote path:

```text
~/stream-stack
```

During installation the GUI:

- checks Git, Python, Docker and Docker Compose;
- optionally installs missing prerequisites on Ubuntu;
- clones the repo, or performs `git pull --ff-only` when it already exists;
- uploads the complete `setup.env`;
- runs `./setup.sh --non-interactive`;
- therefore uses the same Headscale/Jackett runtime-key automation and NPM desired-state automation as the CLI installer;
- optionally runs `docker compose --profile all up -d`;
- displays `docker compose --profile all ps` in the log when finished.

The GUI does not reimplement the stack logic. The Linux scripts remain the single source of truth; Windows only collects inputs and orchestrates them remotely.

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

Disable `Use standard hostnames` to type any full hostname for each service. Those hostnames are written to `setup.env` and are therefore consumed by the same Linux renderer and NPM automation.

## Still manual by design

Application database/account state is not fabricated by the Windows wizard. After deployment the remaining expected steps are:

- AdGuard Home first-run wizard;
- add the operator's own Jackett indexers/accounts;
- import the sanitized AIOStreams JSON and enter provider/indexer/Usenet credentials;
- verify streaming behavior and AIOStreams variants.

The final page provides shortcuts for the main local/public UIs.
