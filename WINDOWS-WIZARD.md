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

AdGuard Home is outside this Compose; LAN DNS is expected to be provided by a separate resolver/AdGuard instance. Private application state such as Jackett indexers and the AIOStreams runtime backup remains operator-specific.

For a standalone executable:

```powershell
.\build.ps1
```

or use the `StreamStackSetupWizard-Windows` artifact produced by GitHub Actions.
