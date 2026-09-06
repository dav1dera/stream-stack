# Windows graphical setup

A Windows GUI is available in [`windows-wizard/`](windows-wizard/README.md).

Quick start:

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

Before a fresh public install, forward on the router:

```text
TCP 80  -> SERVER_LAN_IP:80
TCP 443 -> SERVER_LAN_IP:443
```

The GUI configures the headless Ubuntu Docker server over SSH/SFTP and uses the same `setup.sh`, NPM automation and templates as the CLI installer.

With the recommended defaults:

```text
Avvia stack completo           ON
Strict Acceptance              ON
Public readiness timeout       600 s
Auto NPM                       ON
Auto runtime keys              ON
```

the wizard waits for public DNS, obtains HTTPS, starts the full Compose profile and runs `scripts/acceptance.py`. It shows **Completato** only after the strict end-to-end checks pass.

The final page also probes published LAN ports from the Windows PC and shows `OK/KO`, the local address and an **Apri** button for each main web service.

## AIOStreams reference configuration

The repository now includes a sanitized AIOStreams reference template. `setup.sh` renders a local copy using the credentials/domains generated for the new installation:

```text
data/aiostreams/runtime-template.json
```

The Windows completion page exposes:

```text
Salva JSON per import AIOStreams
```

Use that file from **AIOStreams -> Save & Install -> Backups -> Import**.

The tracked template itself contains no live credentials. The rendered JSON does contain values for the new installation, so it is created mode `0600`, is gitignored, and must not be published or shared. See [`docs/AIOSTREAMS-TEMPLATE.md`](docs/AIOSTREAMS-TEMPLATE.md) for the sanitization and validation model.

AdGuard Home is outside this Compose; LAN DNS is expected to be provided by a separate resolver/AdGuard instance. Private application state that cannot be safely fabricated, especially Jackett indexers/accounts and external provider/indexer/Usenet credentials, remains operator-specific.

For a standalone executable:

```powershell
.\build.ps1
```

or use the `StreamStackSetupWizard-Windows` artifact produced by GitHub Actions.
